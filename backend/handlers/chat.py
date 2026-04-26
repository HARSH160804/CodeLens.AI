"""
Lambda handler for conversational codebase chat using RAG.
Implements FR-4.1, FR-4.2, FR-4.3, FR-4.4, FR-4.5, FR-4.6 from requirements.
"""
import json
import os
import uuid
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError

# Import custom libraries
import sys
sys.path.append('/opt/python')  # Lambda layer path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))

from bedrock_client import BedrockClient, CHAT_SYSTEM_PROMPT
from vector_store import DynamoDBVectorStore


# Initialize shared resources
bedrock_client = BedrockClient()
vector_store = DynamoDBVectorStore()
dynamodb = boto3.resource('dynamodb')
repos_table = dynamodb.Table(os.environ.get('REPOSITORIES_TABLE', 'BloomWay-Repositories'))
sessions_table = dynamodb.Table(os.environ.get('SESSIONS_TABLE', 'BloomWay-Sessions'))

# Constants
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
}
MAX_CONTEXT_CHUNKS = 5
MAX_HISTORY_MESSAGES = 5


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process chat queries using retrieval-augmented generation.
    
    Request body:
        {
            "message": "string",
            "session_id": "uuid" (optional, will create if not provided),
            "scope": {
                "type": "all"|"file"|"directory",
                "path": "string" (required for file/directory)
            },
            "history": [
                {"role": "user"|"assistant", "content": "string"}
            ]
        }
    
    Returns:
        {
            "repo_id": "uuid",
            "response": "string with citations like [src/api.js:45]",
            "citations": [
                {"file": "src/api.js", "line": 45, "snippet": "..."}
            ],
            "suggested_questions": ["Question 1", "Question 2"],
            "confidence": "high"|"medium"|"low",
            "session_id": "uuid"
        }
    """
    try:
        # Extract parameters
        repo_id = event.get('pathParameters', {}).get('id')
        
        if not repo_id:
            return _error_response(400, "Repository ID is required")
        
        body = json.loads(event.get('body', '{}'))
        message = body.get('message')
        session_id = body.get('session_id')
        scope = body.get('scope', {'type': 'all'})
        history = body.get('history', [])
        
        if not message:
            return _error_response(400, "Message is required")
        
        print(f"Chat request for repo_id: {repo_id}, message: {message[:100]}")
        
        # Step 1: Validate or create session
        if not session_id:
            session_id = str(uuid.uuid4())
            print(f"Created new session: {session_id}")
        
        session_data = _validate_or_create_session(repo_id, session_id)
        if not session_data:
            return _error_response(404, f"Repository {repo_id} not found")
        
        # Step 2: Generate embedding for user message
        print("Generating embedding for user message...")
        try:
            query_embedding = bedrock_client.generate_embedding(message)
            print(f"✓ Query embedding generated. Length: {len(query_embedding)}, Type: {type(query_embedding)}")
        except Exception as e:
            print(f"Failed to generate embedding: {str(e)}")
            return _error_response(500, f"Failed to process message: {str(e)}")
        
        # Step 3: Retrieve relevant context from vector store
        print(f"Retrieving context with scope: {scope}")
        print(f"DEBUG: repo_id={repo_id}, type={type(repo_id)}")
        context_chunks = _retrieve_context(repo_id, query_embedding, scope)
        print(f"✓ Retrieved {len(context_chunks)} context chunks")
        
        if not context_chunks:
            return _error_response(404, "No relevant code found in repository")
        
        # Step 4: Calculate confidence based on context relevance
        confidence = _calculate_confidence(context_chunks)
        
        # Step 5: Build RAG prompt
        rag_prompt = _build_rag_prompt(message, context_chunks, history)
        
        # Step 6: Call Bedrock for response
        print("Generating response with Bedrock...")
        try:
            response_text = bedrock_client.invoke_claude(
                prompt=rag_prompt,
                system_prompt=CHAT_SYSTEM_PROMPT,
                max_tokens=2048,
                temperature=0.7
            )
        except Exception as e:
            print(f"Failed to generate response: {str(e)}")
            return _error_response(500, f"Failed to generate response: {str(e)}")
        
        # Step 7: Parse citations from response
        citations = _extract_citations(response_text, context_chunks)
        
        # Step 8: Generate suggested follow-up questions
        suggested_questions = _generate_suggested_questions(message, context_chunks, response_text)
        
        # Step 9: Store conversation in DynamoDB
        _store_conversation(session_id, repo_id, message, response_text)
        
        # Step 10: Build response
        timestamp = datetime.utcnow().isoformat() + 'Z'
        result = {
            'repo_id': repo_id,
            'response': response_text,
            'citations': citations,
            'suggested_questions': suggested_questions,
            'confidence': confidence,
            'session_id': session_id,
            'timestamp': timestamp
        }
        
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps(result)
        }
        
    except json.JSONDecodeError:
        return _error_response(400, "Invalid JSON in request body")
    
    except Exception as e:
        print(f"Unexpected error in chat handler: {str(e)}")
        import traceback
        traceback.print_exc()
        return _error_response(500, f"Internal server error: {str(e)}")


def _validate_or_create_session(repo_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    """Validate session exists or create new one."""
    try:
        # Check if repository exists
        repo_response = repos_table.get_item(Key={'repo_id': repo_id})
        if 'Item' not in repo_response:
            return None
        
        # Check if session exists
        try:
            session_response = sessions_table.get_item(Key={'session_id': session_id})
            if 'Item' in session_response:
                print(f"Using existing session: {session_id}")
                return session_response['Item']
        except ClientError:
            pass
        
        # Create new session
        ttl = int((datetime.utcnow() + timedelta(hours=24)).timestamp())
        session_data = {
            'session_id': session_id,
            'repo_id': repo_id,
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'ttl': ttl,
            'message_count': 0
        }
        
        sessions_table.put_item(Item=session_data)
        print(f"Created new session: {session_id}")
        
        return session_data
        
    except Exception as e:
        print(f"Session validation error: {str(e)}")
        return None


def _retrieve_context(repo_id: str, query_embedding: List[float], scope: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Retrieve relevant context chunks based on scope."""
    scope_type = scope.get('type', 'all')
    scope_path = scope.get('path', '')
    
    # Search vector store
    all_chunks = vector_store.search(repo_id, query_embedding, top_k=20)
    
    # Filter based on scope
    if scope_type == 'file' and scope_path:
        filtered_chunks = [c for c in all_chunks if c['file_path'] == scope_path]
    elif scope_type == 'directory' and scope_path:
        filtered_chunks = [c for c in all_chunks if c['file_path'].startswith(scope_path)]
    else:
        filtered_chunks = all_chunks
    
    # Return top chunks
    return filtered_chunks[:MAX_CONTEXT_CHUNKS]


def _calculate_confidence(chunks: List[Dict[str, Any]]) -> str:
    """Calculate confidence level based on similarity scores."""
    if not chunks:
        return 'low'
    
    avg_similarity = sum(c.get('similarity', 0) for c in chunks) / len(chunks)
    
    if avg_similarity > 0.8:
        return 'high'
    elif avg_similarity > 0.6:
        return 'medium'
    else:
        return 'low'


def _build_rag_prompt(message: str, context_chunks: List[Dict[str, Any]], history: List[Dict[str, Any]]) -> str:
    """Build RAG prompt with context and history."""
    # Build context section
    context_parts = []
    for i, chunk in enumerate(context_chunks, 1):
        file_path = chunk['file_path']
        content = chunk['content']
        metadata = chunk.get('metadata', {})
        start_line = metadata.get('start_line', 'unknown')
        
        context_parts.append(f"""
Context {i} - File: {file_path} (Line {start_line})
```
{content[:500]}
```
""")
    
    context_str = '\n'.join(context_parts)
    
    # Build history section
    history_str = ''
    if history:
        recent_history = history[-MAX_HISTORY_MESSAGES:]
        history_parts = []
        for msg in recent_history:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            history_parts.append(f"{role.capitalize()}: {content}")
        history_str = '\n\nConversation History:\n' + '\n'.join(history_parts)
    
    # Build full prompt
    prompt = f"""You are helping a developer understand a codebase. Answer their question using the provided code context.

Relevant Code Context:
{context_str}
{history_str}

Developer's Question: {message}

Instructions:
1. Answer based on the provided code context
2. Include file references in your answer using format [filename:line]
3. If the context doesn't contain enough information, say so clearly
4. Provide code examples when helpful
5. Be concise but thorough

Answer:"""
    
    return prompt


def _extract_citations(response: str, context_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract citation references from response."""
    citations = []
    
    # Find citation patterns like [filename:line] or [filename]
    citation_pattern = r'\[([^\]]+):(\d+)\]|\[([^\]]+)\]'
    matches = re.finditer(citation_pattern, response)
    
    seen_citations = set()
    
    for match in matches:
        if match.group(1):  # [filename:line]
            file_path = match.group(1)
            line = int(match.group(2))
        else:  # [filename]
            file_path = match.group(3)
            line = None
        
        citation_key = f"{file_path}:{line}" if line else file_path
        
        if citation_key not in seen_citations:
            # Find matching chunk
            snippet = ''
            for chunk in context_chunks:
                if chunk['file_path'] == file_path:
                    snippet = chunk['content'][:200] + '...'
                    break
            
            citations.append({
                'file': file_path,
                'line': line,
                'snippet': snippet
            })
            seen_citations.add(citation_key)
    
    # If no explicit citations, add top context files
    if not citations:
        for chunk in context_chunks[:3]:
            file_path = chunk['file_path']
            metadata = chunk.get('metadata', {})
            line = metadata.get('start_line')
            
            citations.append({
                'file': file_path,
                'line': line,
                'snippet': chunk['content'][:200] + '...'
            })
    
    return citations[:5]


def _generate_suggested_questions(message: str, context_chunks: List[Dict[str, Any]], response: str) -> List[str]:
    """Generate suggested follow-up questions."""
    suggestions = []
    
    # Extract file types from context
    file_types = set()
    for chunk in context_chunks:
        file_path = chunk['file_path']
        if '.' in file_path:
            ext = file_path.split('.')[-1]
            file_types.add(ext)
    
    # Generic suggestions based on context
    if any(ext in ['py', 'js', 'ts', 'java'] for ext in file_types):
        suggestions.extend([
            "How does error handling work in this code?",
            "What are the main functions and their purposes?",
            "Are there any design patterns used here?"
        ])
    
    # Add context-specific suggestions
    if 'test' in message.lower() or any('test' in c['file_path'].lower() for c in context_chunks):
        suggestions.append("What testing strategy is used?")
    
    if 'api' in message.lower() or any('api' in c['file_path'].lower() for c in context_chunks):
        suggestions.append("What API endpoints are available?")
    
    if 'database' in message.lower() or 'db' in message.lower():
        suggestions.append("How is data persistence handled?")
    
    # Limit to 3 suggestions
    return suggestions[:3]


def _store_conversation(session_id: str, repo_id: str, message: str, response: str) -> None:
    """Store conversation turn in DynamoDB."""
    try:
        # Update session with new message
        sessions_table.update_item(
            Key={'session_id': session_id},
            UpdateExpression='SET message_count = if_not_exists(message_count, :zero) + :inc, last_message_at = :timestamp',
            ExpressionAttributeValues={
                ':zero': 0,
                ':inc': 1,
                ':timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        )
        
        print(f"Updated session {session_id} with new message")
        
    except Exception as e:
        print(f"Failed to store conversation: {str(e)}")
        # Non-critical, continue


def _error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create standardized error response."""
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps({
            'error': message,
            'status_code': status_code
        })
    }
