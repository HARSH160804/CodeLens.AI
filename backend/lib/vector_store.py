"""DynamoDB-backed vector store for semantic code search.

Replaces the previous InMemoryVectorStore to ensure persistence across
Lambda cold starts. Embeddings are stored in DynamoDB and cosine similarity
is computed application-side using numpy.
"""
import json
import os
import uuid
from typing import List, Dict, Any, Optional
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
import numpy as np


class DynamoDBVectorStore:
    """DynamoDB-backed vector store for code embeddings.
    
    Uses the existing BloomWay-Embeddings table with schema:
        - repo_id (HASH key): Repository identifier
        - chunk_id (RANGE key): Unique chunk identifier (UUID)
    
    Additional attributes per item:
        - file_path: Relative path to the source file
        - content: Code chunk text
        - embedding: JSON-serialized list of floats (1024-dim Titan v2)
        - metadata: JSON map of chunk metadata
    """
    
    MAX_CHUNKS_PER_REPO = 10000
    DYNAMO_BATCH_SIZE = 25  # DynamoDB batch_write_item limit
    
    def __init__(self, table_name: Optional[str] = None, region: Optional[str] = None):
        """
        Initialize DynamoDB vector store.
        
        Args:
            table_name: DynamoDB table name (defaults to EMBEDDINGS_TABLE env var)
            region: AWS region (defaults to AWS_REGION env var)
        """
        self.table_name = table_name or os.environ.get('EMBEDDINGS_TABLE', 'BloomWay-Embeddings')
        region = region or os.environ.get('AWS_REGION', 'us-east-1')
        
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(self.table_name)
    
    def add_chunk(
        self,
        repo_id: str,
        file_path: str,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> None:
        """
        Add a code chunk with its embedding to DynamoDB.
        
        Args:
            repo_id: Repository identifier
            file_path: Path to the file
            content: Code content
            embedding: Embedding vector (list of floats)
            metadata: Additional metadata
            
        Raises:
            ValueError: If repo exceeds max chunks limit
        """
        # Generate a unique chunk_id
        chunk_id = str(uuid.uuid4())
        
        # Normalize the embedding before storage
        embedding_array = np.array(embedding, dtype=np.float32)
        norm = np.linalg.norm(embedding_array)
        if norm > 0:
            embedding_array = embedding_array / norm
        
        # Serialize embedding as JSON string (DynamoDB doesn't support float lists natively)
        embedding_json = json.dumps(embedding_array.tolist())
        
        # Clean metadata — convert any float values to Decimal for DynamoDB
        clean_metadata = self._clean_for_dynamodb(metadata)
        
        try:
            self.table.put_item(Item={
                'repo_id': repo_id,
                'chunk_id': chunk_id,
                'file_path': file_path,
                'content': content,
                'embedding': embedding_json,
                'metadata': clean_metadata
            })
        except ClientError as e:
            print(f"DynamoDB put_item error: {str(e)}")
            raise
    
    def add_chunks_batch(
        self,
        repo_id: str,
        chunks: List[Dict[str, Any]]
    ) -> int:
        """
        Add multiple chunks in batch for efficiency during ingestion.
        
        Args:
            repo_id: Repository identifier
            chunks: List of dicts with keys: file_path, content, embedding, metadata
            
        Returns:
            Number of chunks successfully stored
        """
        stored_count = 0
        
        with self.table.batch_writer() as batch:
            for chunk in chunks:
                try:
                    embedding_array = np.array(chunk['embedding'], dtype=np.float32)
                    norm = np.linalg.norm(embedding_array)
                    if norm > 0:
                        embedding_array = embedding_array / norm
                    
                    embedding_json = json.dumps(embedding_array.tolist())
                    clean_metadata = self._clean_for_dynamodb(chunk.get('metadata', {}))
                    
                    batch.put_item(Item={
                        'repo_id': repo_id,
                        'chunk_id': str(uuid.uuid4()),
                        'file_path': chunk['file_path'],
                        'content': chunk['content'],
                        'embedding': embedding_json,
                        'metadata': clean_metadata
                    })
                    stored_count += 1
                    
                except Exception as e:
                    print(f"Warning: Failed to batch-write chunk: {str(e)}")
                    continue
        
        return stored_count
    
    def search(
        self,
        repo_id: str,
        query_embedding: List[float],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for most similar chunks using cosine similarity.
        
        Fetches all chunks for the repo from DynamoDB, computes cosine
        similarity in Python, and returns top-K results.
        
        Args:
            repo_id: Repository identifier
            query_embedding: Query embedding vector
            top_k: Number of results to return
            
        Returns:
            List of chunks sorted by similarity (highest first)
        """
        print(f"[VectorStore] Searching for repo_id: {repo_id}")
        print(f"[VectorStore] Query embedding length: {len(query_embedding)}")
        
        # Fetch all chunks for this repo
        all_items = self._query_all_chunks(repo_id)
        
        print(f"[VectorStore] Retrieved {len(all_items)} chunks from DynamoDB")
        
        if not all_items:
            print(f"[VectorStore] WARNING: No chunks found for repo_id: {repo_id}")
            return []
        
        # Log sample chunk for debugging
        if all_items:
            sample = all_items[0]
            print(f"[VectorStore] Sample chunk - repo_id: {sample.get('repo_id')}, file_path: {sample.get('file_path')}")
            if 'embedding' in sample:
                try:
                    sample_embedding = json.loads(sample['embedding'])
                    print(f"[VectorStore] Sample embedding length: {len(sample_embedding)}")
                except Exception as e:
                    print(f"[VectorStore] ERROR parsing sample embedding: {str(e)}")
        
        # Normalize query embedding
        query_array = np.array(query_embedding, dtype=np.float32)
        norm = np.linalg.norm(query_array)
        if norm > 0:
            query_array = query_array / norm
        
        # Compute cosine similarity for each chunk
        results = []
        for item in all_items:
            try:
                embedding = np.array(json.loads(item['embedding']), dtype=np.float32)
                similarity = float(np.dot(embedding, query_array))
                
                results.append({
                    'repo_id': item['repo_id'],
                    'file_path': item['file_path'],
                    'content': item['content'],
                    'metadata': item.get('metadata', {}),
                    'similarity': similarity
                })
            except Exception as e:
                print(f"Warning: Failed to process chunk {item.get('chunk_id')}: {str(e)}")
                continue
        
        # Sort by similarity (highest first) and return top-K
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]
    
    def get_file_chunks(self, repo_id: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a specific file.
        
        Args:
            repo_id: Repository identifier
            file_path: Path to the file
            
        Returns:
            List of chunks for the file
        """
        try:
            # Query by repo_id and filter by file_path
            response = self.table.query(
                KeyConditionExpression=Key('repo_id').eq(repo_id),
                FilterExpression=Attr('file_path').eq(file_path)
            )
            
            items = response.get('Items', [])
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.query(
                    KeyConditionExpression=Key('repo_id').eq(repo_id),
                    FilterExpression=Attr('file_path').eq(file_path),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                items.extend(response.get('Items', []))
            
            chunks = []
            for item in items:
                chunks.append({
                    'repo_id': item['repo_id'],
                    'file_path': item['file_path'],
                    'content': item['content'],
                    'metadata': item.get('metadata', {})
                })
            
            return chunks
            
        except ClientError as e:
            print(f"DynamoDB query error in get_file_chunks: {str(e)}")
            return []
    
    def delete_repo(self, repo_id: str) -> None:
        """
        Delete all chunks for a repository.
        
        Args:
            repo_id: Repository identifier
        """
        try:
            # Query all chunk_ids for this repo
            items_to_delete = []
            response = self.table.query(
                KeyConditionExpression=Key('repo_id').eq(repo_id),
                ProjectionExpression='repo_id, chunk_id'
            )
            items_to_delete.extend(response.get('Items', []))
            
            while 'LastEvaluatedKey' in response:
                response = self.table.query(
                    KeyConditionExpression=Key('repo_id').eq(repo_id),
                    ProjectionExpression='repo_id, chunk_id',
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                items_to_delete.extend(response.get('Items', []))
            
            # Batch delete
            with self.table.batch_writer() as batch:
                for item in items_to_delete:
                    batch.delete_item(Key={
                        'repo_id': item['repo_id'],
                        'chunk_id': item['chunk_id']
                    })
            
            print(f"Deleted {len(items_to_delete)} chunks for repo {repo_id}")
            
        except ClientError as e:
            print(f"DynamoDB delete error: {str(e)}")
            raise
    
    def _query_all_chunks(self, repo_id: str) -> List[Dict[str, Any]]:
        """
        Query all chunks for a repository from DynamoDB.
        
        Handles pagination automatically.
        
        Args:
            repo_id: Repository identifier
            
        Returns:
            List of all DynamoDB items for the repo
        """
        try:
            print(f"[VectorStore] Querying DynamoDB table: {self.table_name}")
            print(f"[VectorStore] Query condition: repo_id = {repo_id}")
            
            items = []
            response = self.table.query(
                KeyConditionExpression=Key('repo_id').eq(repo_id)
            )
            items.extend(response.get('Items', []))
            
            print(f"[VectorStore] First query returned {len(response.get('Items', []))} items")
            
            while 'LastEvaluatedKey' in response:
                response = self.table.query(
                    KeyConditionExpression=Key('repo_id').eq(repo_id),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                items.extend(response.get('Items', []))
                print(f"[VectorStore] Pagination: fetched {len(response.get('Items', []))} more items")
            
            print(f"[VectorStore] Total items retrieved: {len(items)}")
            return items
            
        except ClientError as e:
            print(f"[VectorStore] DynamoDB query error: {str(e)}")
            print(f"[VectorStore] Error code: {e.response.get('Error', {}).get('Code', 'Unknown')}")
            print(f"[VectorStore] Error message: {e.response.get('Error', {}).get('Message', 'Unknown')}")
            return []
    
    def _clean_for_dynamodb(self, obj: Any) -> Any:
        """
        Recursively convert Python types to DynamoDB-compatible types.
        
        Converts float to Decimal to avoid DynamoDB Float type issues.
        
        Args:
            obj: Object to clean
            
        Returns:
            DynamoDB-compatible object
        """
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: self._clean_for_dynamodb(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._clean_for_dynamodb(v) for v in obj]
        elif isinstance(obj, (int, str, bool, type(None))):
            return obj
        else:
            return str(obj)
