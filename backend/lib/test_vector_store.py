#!/usr/bin/env python3
"""Test script for DynamoDBVectorStore using moto mock."""

import json
import os
import sys

# Set environment variables before importing boto3
os.environ['EMBEDDINGS_TABLE'] = 'BloomWay-Embeddings-Test'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'

import boto3
import numpy as np

try:
    from moto import mock_dynamodb
except ImportError:
    # moto v5+ uses mock_aws
    try:
        from moto import mock_aws as mock_dynamodb
    except ImportError:
        print("ERROR: moto library not installed. Install with: pip install moto")
        sys.exit(1)

from vector_store import DynamoDBVectorStore


def generate_fake_embedding(seed: int, dim: int = 1024) -> list:
    """Generate deterministic fake embedding."""
    np.random.seed(seed)
    return np.random.randn(dim).tolist()


def create_mock_table():
    """Create mock DynamoDB table matching the BloomWay-Embeddings schema."""
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.create_table(
        TableName='BloomWay-Embeddings-Test',
        KeySchema=[
            {'AttributeName': 'repo_id', 'KeyType': 'HASH'},
            {'AttributeName': 'chunk_id', 'KeyType': 'RANGE'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'repo_id', 'AttributeType': 'S'},
            {'AttributeName': 'chunk_id', 'AttributeType': 'S'}
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    return table


@mock_dynamodb
def main():
    print("=" * 60)
    print("DynamoDBVectorStore Test")
    print("=" * 60)
    print()

    # Create mock table
    create_mock_table()

    # Initialize store
    print("1. Initializing DynamoDBVectorStore...")
    store = DynamoDBVectorStore(
        table_name='BloomWay-Embeddings-Test',
        region='us-east-1'
    )
    print("✓ Store initialized")
    print()

    # Add chunks
    print("2. Adding chunks to store...")
    repo_id = "test-repo-123"

    chunks_data = [
        ("src/main.py", "def main(): print('hello')", {"start_line": 1}),
        ("src/main.py", "if __name__ == '__main__': main()", {"start_line": 5}),
        ("src/utils.py", "def helper(): return 42", {"start_line": 1}),
        ("src/utils.py", "def another(): return 'test'", {"start_line": 10}),
        ("tests/test_main.py", "def test_main(): assert True", {"start_line": 1}),
    ]

    for i, (file_path, content, metadata) in enumerate(chunks_data):
        embedding = generate_fake_embedding(seed=i)
        store.add_chunk(repo_id, file_path, content, embedding, metadata)
        print(f"  Added chunk {i+1}: {file_path}")

    print(f"✓ Added {len(chunks_data)} chunks via add_chunk")
    print()

    # Search
    print("3. Performing similarity search...")
    query_embedding = generate_fake_embedding(seed=0)
    results = store.search(repo_id, query_embedding, top_k=3)

    print(f"✓ Found {len(results)} results (top_k=3)")
    for i, result in enumerate(results, 1):
        print(f"  Result {i}:")
        print(f"    File: {result['file_path']}")
        print(f"    Similarity: {result['similarity']:.4f}")
        print(f"    Content: {result['content'][:40]}...")

    # Verify results are sorted by similarity
    if len(results) > 1:
        similarities = [r['similarity'] for r in results]
        is_sorted = all(similarities[i] >= similarities[i+1] for i in range(len(similarities)-1))
        if is_sorted:
            print("✓ Results are sorted by similarity (highest first)")
        else:
            print("✗ Results are NOT sorted correctly")
            return False
    print()

    # Get file chunks
    print("4. Retrieving chunks for specific file...")
    file_path = "src/main.py"
    file_chunks = store.get_file_chunks(repo_id, file_path)

    print(f"✓ Found {len(file_chunks)} chunks for {file_path}")
    for i, chunk in enumerate(file_chunks, 1):
        print(f"  Chunk {i}: {chunk['content'][:40]}...")

    # Verify only chunks for the specified file are returned
    all_match = all(chunk['file_path'] == file_path for chunk in file_chunks)
    if all_match and len(file_chunks) == 2:
        print(f"✓ All chunks belong to {file_path}")
    else:
        print(f"✗ Expected 2 chunks for {file_path}, got {len(file_chunks)}")
        return False
    print()

    # Test batch add
    print("5. Testing batch add...")
    batch_repo_id = "batch-test-repo"
    batch_chunks = [
        {
            'file_path': 'app.py',
            'content': 'from flask import Flask',
            'embedding': generate_fake_embedding(seed=100),
            'metadata': {'start_line': 1}
        },
        {
            'file_path': 'app.py',
            'content': 'app = Flask(__name__)',
            'embedding': generate_fake_embedding(seed=101),
            'metadata': {'start_line': 2}
        },
        {
            'file_path': 'models.py',
            'content': 'class User: pass',
            'embedding': generate_fake_embedding(seed=102),
            'metadata': {'start_line': 1}
        }
    ]

    stored = store.add_chunks_batch(batch_repo_id, batch_chunks)
    print(f"✓ Batch added {stored} chunks")

    # Verify batch results
    batch_results = store.search(batch_repo_id, generate_fake_embedding(seed=100), top_k=10)
    if len(batch_results) == 3:
        print(f"✓ All {len(batch_results)} batch chunks retrievable via search")
    else:
        print(f"✗ Expected 3 batch chunks, found {len(batch_results)}")
        return False
    print()

    # Delete repo
    print("6. Deleting repository...")
    store.delete_repo(repo_id)
    print(f"✓ Deleted repo: {repo_id}")

    # Verify deletion
    results_after_delete = store.search(repo_id, query_embedding, top_k=5)
    if len(results_after_delete) == 0:
        print("✓ Search returns empty results after deletion")
    else:
        print(f"✗ Search still returns {len(results_after_delete)} results after deletion")
        return False

    file_chunks_after_delete = store.get_file_chunks(repo_id, file_path)
    if len(file_chunks_after_delete) == 0:
        print("✓ get_file_chunks returns empty results after deletion")
    else:
        print(f"✗ get_file_chunks still returns {len(file_chunks_after_delete)} results after deletion")
        return False

    # Verify batch repo is unaffected
    batch_remaining = store.search(batch_repo_id, generate_fake_embedding(seed=100), top_k=10)
    if len(batch_remaining) == 3:
        print("✓ Batch repo unaffected by deletion of other repo")
    else:
        print(f"✗ Batch repo affected: expected 3, found {len(batch_remaining)}")
        return False
    print()

    # Search on non-existent repo
    print("7. Testing search on non-existent repo...")
    empty_results = store.search("non-existent-repo", query_embedding, top_k=5)
    if len(empty_results) == 0:
        print("✓ Search on non-existent repo returns empty list")
    else:
        print(f"✗ Expected empty results, got {len(empty_results)}")
        return False
    print()

    print("=" * 60)
    print("All tests completed successfully!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
