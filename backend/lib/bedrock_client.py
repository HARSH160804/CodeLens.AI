"""Amazon Bedrock client for LLM and embedding operations."""
import json
import time
import boto3
from typing import List, Dict, Any, Optional, Generator
from botocore.exceptions import ClientError


# Prompt Templates
ARCHITECTURE_SYSTEM_PROMPT = """You are an expert software architect analyzing codebases. Your task is to:

1. Analyze the repository structure and identify architectural patterns (MVC, microservices, layered, etc.)
2. Identify entry points (main files, API endpoints, CLI commands)
3. Map data flow between components
4. Identify key dependencies and their relationships
5. Highlight design patterns and best practices used

Provide a clear, structured analysis that helps developers quickly understand the codebase architecture."""

FILE_EXPLAIN_PROMPT = """Explain the following code file at a {level} level:

File: {file_path}

Code:
```
{code_content}
```

Explanation guidelines for {level} level:
- beginner: Use simple terminology, explain high-level purpose, avoid technical jargon
- intermediate: Include implementation details, design patterns, and how it fits in the system
- advanced: Cover optimization techniques, edge cases, architectural implications, and trade-offs

Provide a clear, concise explanation appropriate for the {level} level."""

CHAT_SYSTEM_PROMPT = """You are an AI assistant helping developers understand a codebase. You have access to relevant code snippets retrieved from the repository.

Guidelines:
1. Answer questions based on the provided code context
2. Cite specific files and line numbers when referencing code
3. If the context doesn't contain enough information, say so clearly
4. Provide code examples when helpful
5. Be concise but thorough

Always reference the source files in your answers."""

DIAGRAM_GENERATION_PROMPT = """Based on the following architecture analysis, generate a Mermaid.js flowchart diagram that visualizes:

1. Major system components
2. Dependencies between components
3. Data flow directions
4. External services or APIs

Architecture Analysis:
{architecture_summary}

Generate ONLY the Mermaid.js diagram code (starting with ```mermaid and ending with ```). Use appropriate diagram types (graph, flowchart, or C4 diagram) based on the architecture."""


class BedrockClient:
    """Client for interacting with Amazon Bedrock models."""
    
    def __init__(self, region: str = 'us-east-1'):
        """
        Initialize Bedrock client.
        
        Args:
            region: AWS region for Bedrock service
        """
        self.client = boto3.client('bedrock-runtime', region_name=region)
        self.llm_model_id = 'amazon.nova-lite-v1:0'
        self.embedding_model_id = 'amazon.titan-embed-text-v2:0'
        self.max_retries = 3
        self.base_delay = 1.0  # seconds
    
    def _retry_with_backoff(self, func, *args, **kwargs) -> Any:
        """
        Execute function with exponential backoff retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result from func
            
        Raises:
            ClientError: If all retries fail
        """
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                
                # Don't retry on validation errors
                if error_code in ['ValidationException', 'AccessDeniedException']:
                    raise
                
                # Retry on throttling or service errors
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    time.sleep(delay)
                else:
                    raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector using Amazon Titan Embeddings v2.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector (1024 dimensions for Titan v2)
            
        Raises:
            ClientError: If Bedrock API call fails
        """
        def _invoke():
            body = json.dumps({
                "inputText": text
            })
            
            response = self.client.invoke_model(
                modelId=self.embedding_model_id,
                body=body,
                contentType='application/json',
                accept='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['embedding']
        
        return self._retry_with_backoff(_invoke)
    
    def invoke_claude(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None, 
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        """
        Invoke LLM for text generation via Amazon Bedrock.
        
        Args:
            prompt: User prompt/question
            system_prompt: Optional system prompt for context
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            
        Returns:
            Generated text response
            
        Raises:
            ClientError: If Bedrock API call fails
        """
        def _invoke():
            body = {
                "inferenceConfig": {
                    "max_new_tokens": max_tokens,
                    "temperature": temperature
                },
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ]
            }
            
            if system_prompt:
                body["system"] = [{"text": system_prompt}]
            
            response = self.client.invoke_model(
                modelId=self.llm_model_id,
                body=json.dumps(body),
                contentType='application/json',
                accept='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['output']['message']['content'][0]['text']
        
        return self._retry_with_backoff(_invoke)
    
    def invoke_claude_streaming(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None, 
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> Generator[str, None, None]:
        """
        Invoke LLM with streaming response.
        
        Args:
            prompt: User prompt/question
            system_prompt: Optional system prompt for context
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            
        Yields:
            Text chunks as they are generated
            
        Raises:
            ClientError: If Bedrock API call fails
        """
        body = {
            "inferenceConfig": {
                "max_new_tokens": max_tokens,
                "temperature": temperature
            },
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ]
        }
        
        if system_prompt:
            body["system"] = [{"text": system_prompt}]
        
        response = self.client.invoke_model_with_response_stream(
            modelId=self.llm_model_id,
            body=json.dumps(body),
            contentType='application/json',
            accept='application/json'
        )
        
        stream = response['body']
        for event in stream:
            chunk = event.get('chunk')
            if chunk:
                chunk_data = json.loads(chunk['bytes'].decode())
                
                if chunk_data.get('type') == 'content_block_delta':
                    if 'delta' in chunk_data and 'text' in chunk_data['delta']:
                        yield chunk_data['delta']['text']
                elif 'contentBlockDelta' in chunk_data:
                    delta = chunk_data['contentBlockDelta'].get('delta', {})
                    if 'text' in delta:
                        yield delta['text']
    
    def generate_architecture_summary(self, repo_structure: str) -> str:
        """
        Generate architecture summary from repository structure.
        
        Args:
            repo_structure: String representation of repository structure
            
        Returns:
            Architecture analysis text
        """
        prompt = f"""Analyze this repository structure and provide an architecture summary:

{repo_structure}

Identify:
1. Architectural pattern (MVC, microservices, etc.)
2. Entry points
3. Key components and their responsibilities
4. Data flow
5. External dependencies"""
        
        return self.invoke_claude(
            prompt=prompt,
            system_prompt=ARCHITECTURE_SYSTEM_PROMPT,
            max_tokens=2048
        )
    
    def explain_file(
        self, 
        file_path: str, 
        code_content: str, 
        level: str = 'intermediate'
    ) -> str:
        """
        Generate file explanation at specified complexity level.
        
        Args:
            file_path: Path to the file
            code_content: Content of the file
            level: Explanation level (beginner/intermediate/advanced)
            
        Returns:
            File explanation text
        """
        prompt = FILE_EXPLAIN_PROMPT.format(
            level=level,
            file_path=file_path,
            code_content=code_content
        )
        
        return self.invoke_claude(
            prompt=prompt,
            max_tokens=2048
        )
    
    def generate_mermaid_diagram(self, architecture_summary: str) -> str:
        """
        Generate Mermaid.js diagram from architecture summary.
        
        Args:
            architecture_summary: Architecture analysis text
            
        Returns:
            Mermaid.js diagram code
        """
        prompt = DIAGRAM_GENERATION_PROMPT.format(
            architecture_summary=architecture_summary
        )
        
        response = self.invoke_claude(
            prompt=prompt,
            max_tokens=1024
        )
        
        # Extract mermaid code block
        if '```mermaid' in response:
            start = response.find('```mermaid') + 10
            end = response.find('```', start)
            return response[start:end].strip()
        
        return response.strip()
    
    def answer_question_with_context(
        self, 
        question: str, 
        code_contexts: List[Dict[str, str]]
    ) -> str:
        """
        Answer question using RAG with code context.
        
        Args:
            question: User's question
            code_contexts: List of dicts with 'file_path' and 'content' keys
            
        Returns:
            Answer with citations
        """
        context_str = "\n\n".join([
            f"File: {ctx['file_path']}\n```\n{ctx['content']}\n```"
            for ctx in code_contexts
        ])
        
        prompt = f"""Question: {question}

Relevant Code Context:
{context_str}

Please answer the question based on the provided code context. Cite specific files when referencing code."""
        
        return self.invoke_claude(
            prompt=prompt,
            system_prompt=CHAT_SYSTEM_PROMPT,
            max_tokens=2048
        )


def count_tokens(text: str) -> int:
    """
    Estimate token count for text.
    
    Uses a simple heuristic: ~4 characters per token for English text.
    For production, consider using tiktoken library.
    
    Args:
        text: Text to count tokens for
        
    Returns:
        Estimated token count
    """
    # Simple heuristic: average 4 characters per token
    return len(text) // 4


def truncate_to_context(text: str, max_tokens: int) -> str:
    """
    Truncate text to fit within token limit.
    
    Args:
        text: Text to truncate
        max_tokens: Maximum number of tokens
        
    Returns:
        Truncated text
    """
    estimated_tokens = count_tokens(text)
    
    if estimated_tokens <= max_tokens:
        return text
    
    # Calculate character limit based on token limit
    char_limit = max_tokens * 4
    
    # Truncate and add ellipsis
    if len(text) > char_limit:
        return text[:char_limit - 3] + "..."
    
    return text
