# BedrockClient Documentation

## Overview

The `BedrockClient` provides a comprehensive interface for interacting with Amazon Bedrock's AI models, specifically:
- **Claude 3.5 Sonnet v2** for text generation
- **Titan Text Embeddings v2** for vector embeddings

## Features

### Core Capabilities

1. **Text Generation** - Generate responses using Claude 3.5 Sonnet
2. **Streaming Responses** - Stream text generation for real-time UX
3. **Embeddings** - Generate 1024-dimensional vectors for semantic search
4. **Architecture Analysis** - Analyze codebase structure and patterns
5. **File Explanations** - Multi-level code explanations (beginner/intermediate/advanced)
6. **Mermaid Diagrams** - Generate architecture visualizations
7. **RAG Chat** - Answer questions with code context citations

### Built-in Features

- ✅ Exponential backoff retry logic
- ✅ Error handling for throttling and service errors
- ✅ Type hints throughout
- ✅ Comprehensive docstrings
- ✅ Token counting and truncation utilities
- ✅ Pre-configured prompt templates

## Installation

```bash
pip install boto3
```

## Quick Start

```python
from lib.bedrock_client import BedrockClient

# Initialize client
client = BedrockClient(region='us-east-1')

# Generate text
response = client.invoke_claude(
    prompt="Explain microservices architecture",
    max_tokens=500
)

# Generate embedding
embedding = client.generate_embedding("def hello(): print('world')")

# Stream response
for chunk in client.invoke_claude_streaming("Tell me a story"):
    print(chunk, end='', flush=True)
```

## API Reference

### BedrockClient

#### `__init__(region='us-east-1')`

Initialize the Bedrock client.

**Parameters:**
- `region` (str): AWS region for Bedrock service

**Example:**
```python
client = BedrockClient(region='us-west-2')
```

---

#### `generate_embedding(text: str) -> List[float]`

Generate embedding vector using Titan Embeddings v2.

**Parameters:**
- `text` (str): Text to embed

**Returns:**
- `List[float]`: 1024-dimensional embedding vector

**Example:**
```python
embedding = client.generate_embedding("sample code")
print(f"Dimensions: {len(embedding)}")  # 1024
```

---

#### `invoke_claude(prompt, system_prompt=None, max_tokens=4096, temperature=0.7) -> str`

Invoke Claude 3.5 Sonnet for text generation.

**Parameters:**
- `prompt` (str): User prompt/question
- `system_prompt` (str, optional): System prompt for context
- `max_tokens` (int): Maximum tokens to generate (default: 4096)
- `temperature` (float): Sampling temperature 0.0-1.0 (default: 0.7)

**Returns:**
- `str`: Generated text response

**Example:**
```python
response = client.invoke_claude(
    prompt="What is a REST API?",
    system_prompt="You are a helpful coding assistant",
    max_tokens=500,
    temperature=0.5
)
```

---

#### `invoke_claude_streaming(prompt, system_prompt=None, max_tokens=4096, temperature=0.7) -> Generator[str, None, None]`

Invoke Claude with streaming response.

**Parameters:**
- Same as `invoke_claude()`

**Yields:**
- `str`: Text chunks as they are generated

**Example:**
```python
for chunk in client.invoke_claude_streaming("Explain async/await"):
    print(chunk, end='', flush=True)
```

---

#### `generate_architecture_summary(repo_structure: str) -> str`

Generate architecture summary from repository structure.

**Parameters:**
- `repo_structure` (str): String representation of repository structure

**Returns:**
- `str`: Architecture analysis text

**Example:**
```python
structure = """
project/
├── src/
│   ├── controllers/
│   └── models/
└── tests/
"""
summary = client.generate_architecture_summary(structure)
```

---

#### `explain_file(file_path: str, code_content: str, level='intermediate') -> str`

Generate file explanation at specified complexity level.

**Parameters:**
- `file_path` (str): Path to the file
- `code_content` (str): Content of the file
- `level` (str): Explanation level - 'beginner', 'intermediate', or 'advanced'

**Returns:**
- `str`: File explanation text

**Example:**
```python
explanation = client.explain_file(
    file_path="auth.py",
    code_content="def authenticate(user, password): ...",
    level="beginner"
)
```

---

#### `generate_mermaid_diagram(architecture_summary: str) -> str`

Generate Mermaid.js diagram from architecture summary.

**Parameters:**
- `architecture_summary` (str): Architecture analysis text

**Returns:**
- `str`: Mermaid.js diagram code

**Example:**
```python
diagram = client.generate_mermaid_diagram(summary)
print(f"```mermaid\n{diagram}\n```")
```

---

#### `answer_question_with_context(question: str, code_contexts: List[Dict[str, str]]) -> str`

Answer question using RAG with code context.

**Parameters:**
- `question` (str): User's question
- `code_contexts` (List[Dict]): List of dicts with 'file_path' and 'content' keys

**Returns:**
- `str`: Answer with citations

**Example:**
```python
contexts = [
    {'file_path': 'auth.py', 'content': 'def login(): ...'},
    {'file_path': 'user.py', 'content': 'class User: ...'}
]
answer = client.answer_question_with_context(
    "How does authentication work?",
    contexts
)
```

---

### Utility Functions

#### `count_tokens(text: str) -> int`

Estimate token count for text using 4 characters per token heuristic.

**Example:**
```python
from lib.bedrock_client import count_tokens

tokens = count_tokens("Hello world")
print(f"Estimated tokens: {tokens}")
```

---

#### `truncate_to_context(text: str, max_tokens: int) -> str`

Truncate text to fit within token limit.

**Example:**
```python
from lib.bedrock_client import truncate_to_context

truncated = truncate_to_context(long_text, max_tokens=100)
```

---

## Prompt Templates

Pre-configured prompt templates are available as constants:

### `ARCHITECTURE_SYSTEM_PROMPT`

System prompt for architecture analysis. Guides the model to:
- Identify architectural patterns (MVC, microservices, etc.)
- Find entry points
- Map data flow
- Identify dependencies

### `FILE_EXPLAIN_PROMPT`

Template for file explanations with placeholders:
- `{level}`: beginner/intermediate/advanced
- `{file_path}`: Path to the file
- `{code_content}`: File content

### `CHAT_SYSTEM_PROMPT`

System prompt for RAG-based chat. Instructs the model to:
- Answer based on provided code context
- Cite specific files and line numbers
- Provide code examples
- Be concise but thorough

### `DIAGRAM_GENERATION_PROMPT`

Template for Mermaid diagram generation with placeholder:
- `{architecture_summary}`: Architecture analysis text

**Example:**
```python
from lib.bedrock_client import FILE_EXPLAIN_PROMPT

prompt = FILE_EXPLAIN_PROMPT.format(
    level="beginner",
    file_path="app.py",
    code_content="def main(): ..."
)
```

---

## Error Handling

The client includes automatic retry logic with exponential backoff:

- **Retries:** 3 attempts
- **Base delay:** 1 second
- **Backoff:** Exponential (1s, 2s, 4s)
- **No retry on:** ValidationException, AccessDeniedException

**Example:**
```python
try:
    response = client.invoke_claude("test prompt")
except ClientError as e:
    print(f"Error: {e}")
```

---

## Best Practices

### 1. Token Management

```python
# Check token count before sending
text = "..." # long text
if count_tokens(text) > 4000:
    text = truncate_to_context(text, max_tokens=4000)

response = client.invoke_claude(text)
```

### 2. Streaming for Long Responses

```python
# Use streaming for better UX
for chunk in client.invoke_claude_streaming(prompt):
    # Process chunk immediately
    send_to_frontend(chunk)
```

### 3. System Prompts

```python
# Use system prompts for consistent behavior
response = client.invoke_claude(
    prompt=user_question,
    system_prompt=CHAT_SYSTEM_PROMPT
)
```

### 4. Temperature Control

```python
# Lower temperature for factual responses
factual = client.invoke_claude(prompt, temperature=0.3)

# Higher temperature for creative responses
creative = client.invoke_claude(prompt, temperature=0.9)
```

---

## Testing

Run tests with pytest:

```bash
cd backend
pytest tests/test_bedrock_client.py -v
```

---

## Examples

See `backend/examples/bedrock_usage.py` for comprehensive examples:

```bash
cd backend
python examples/bedrock_usage.py
```

---

## Troubleshooting

### Issue: AccessDeniedException

**Cause:** Bedrock model access not enabled

**Solution:** 
1. Go to AWS Console → Amazon Bedrock
2. Click "Model access"
3. Enable Claude 3.5 Sonnet v2 and Titan Embeddings v2

### Issue: ThrottlingException

**Cause:** Too many requests

**Solution:** The client automatically retries with exponential backoff. If persistent, consider:
- Reducing request rate
- Requesting quota increase in AWS Console

### Issue: ValidationException

**Cause:** Invalid parameters (e.g., max_tokens too high)

**Solution:** Check parameter values:
- `max_tokens`: Max 4096 for Claude
- `temperature`: Must be 0.0-1.0

---

## Performance Tips

1. **Batch embeddings** when possible (though current API generates one at a time)
2. **Cache responses** for identical prompts
3. **Use streaming** for long-running generations
4. **Truncate context** to stay within token limits
5. **Adjust temperature** based on use case

---

## License

Part of CodeLens project.
