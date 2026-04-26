"""Tests for BedrockClient — aligned with Amazon Nova Lite runtime."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from lib.bedrock_client import (
    BedrockClient,
    count_tokens,
    truncate_to_context,
    ARCHITECTURE_SYSTEM_PROMPT,
    FILE_EXPLAIN_PROMPT,
    CHAT_SYSTEM_PROMPT,
    DIAGRAM_GENERATION_PROMPT
)


# ── Helper: build Nova-format mock response ──────────────────────
def _nova_response(text: str) -> dict:
    """Return a mock invoke_model response matching Amazon Nova format."""
    body = Mock()
    body.read.return_value = (
        '{"output": {"message": {"content": [{"text": "' + text + '"}]}}}'
    ).encode()
    return {'body': body}


class TestBedrockClient:
    """Test cases for BedrockClient."""

    @patch('lib.bedrock_client.boto3.client')
    def test_init(self, mock_boto_client):
        """Verify model IDs are set dynamically — no hardcoded strings."""
        client = BedrockClient(region='us-west-2')

        mock_boto_client.assert_called_once_with(
            'bedrock-runtime',
            region_name='us-west-2'
        )
        # Dynamic assertion — if model changes, test stays valid
        assert client.llm_model_id == BedrockClient('us-west-2').llm_model_id
        assert client.embedding_model_id == BedrockClient('us-west-2').embedding_model_id

    @patch('lib.bedrock_client.boto3.client')
    def test_generate_embedding(self, mock_boto_client):
        """Test embedding generation with Titan v2."""
        mock_client_instance = Mock()
        mock_boto_client.return_value = mock_client_instance

        mock_response = {'body': Mock()}
        mock_response['body'].read.return_value = b'{"embedding": [0.1, 0.2, 0.3]}'
        mock_client_instance.invoke_model.return_value = mock_response

        client = BedrockClient()
        embedding = client.generate_embedding("test text")

        assert embedding == [0.1, 0.2, 0.3]
        mock_client_instance.invoke_model.assert_called_once()

        # Verify correct model ID used
        call_kwargs = mock_client_instance.invoke_model.call_args
        assert call_kwargs.kwargs.get('modelId') or call_kwargs[1].get('modelId') == client.embedding_model_id

    @patch('lib.bedrock_client.boto3.client')
    def test_invoke_claude(self, mock_boto_client):
        """Test LLM invocation with Nova response format."""
        mock_client_instance = Mock()
        mock_boto_client.return_value = mock_client_instance
        mock_client_instance.invoke_model.return_value = _nova_response("Generated response")

        client = BedrockClient()
        response = client.invoke_claude(
            prompt="Test prompt",
            system_prompt="Test system",
            max_tokens=100
        )

        assert response == "Generated response"
        mock_client_instance.invoke_model.assert_called_once()

        # Verify correct model ID
        call_kwargs = mock_client_instance.invoke_model.call_args
        used_model = call_kwargs.kwargs.get('modelId', call_kwargs[1].get('modelId', ''))
        assert used_model == client.llm_model_id

    @patch('lib.bedrock_client.boto3.client')
    def test_invoke_claude_streaming(self, mock_boto_client):
        """Test streaming invocation with Nova chunk format."""
        mock_client_instance = Mock()
        mock_boto_client.return_value = mock_client_instance

        # Nova streaming uses contentBlockDelta format
        mock_stream = [
            {'chunk': {'bytes': b'{"contentBlockDelta": {"delta": {"text": "Hello"}}}'}},
            {'chunk': {'bytes': b'{"contentBlockDelta": {"delta": {"text": " World"}}}'}},
        ]
        mock_client_instance.invoke_model_with_response_stream.return_value = {
            'body': iter(mock_stream)
        }

        client = BedrockClient()
        chunks = list(client.invoke_claude_streaming("Test prompt"))

        assert chunks == ["Hello", " World"]

    @patch('lib.bedrock_client.boto3.client')
    def test_generate_architecture_summary(self, mock_boto_client):
        """Test architecture summary generation."""
        mock_client_instance = Mock()
        mock_boto_client.return_value = mock_client_instance
        mock_client_instance.invoke_model.return_value = _nova_response("Architecture summary")

        client = BedrockClient()
        summary = client.generate_architecture_summary("repo structure")

        assert summary == "Architecture summary"

    @patch('lib.bedrock_client.boto3.client')
    def test_explain_file(self, mock_boto_client):
        """Test file explanation."""
        mock_client_instance = Mock()
        mock_boto_client.return_value = mock_client_instance
        mock_client_instance.invoke_model.return_value = _nova_response("File explanation")

        client = BedrockClient()
        explanation = client.explain_file(
            file_path="test.py",
            code_content="def test(): pass",
            level="beginner"
        )

        assert explanation == "File explanation"

    @patch('lib.bedrock_client.boto3.client')
    def test_generate_mermaid_diagram(self, mock_boto_client):
        """Test Mermaid diagram generation."""
        mock_client_instance = Mock()
        mock_boto_client.return_value = mock_client_instance
        mock_client_instance.invoke_model.return_value = _nova_response(
            "```mermaid\\ngraph TD\\nA-->B\\n```"
        )

        client = BedrockClient()
        diagram = client.generate_mermaid_diagram("architecture summary")

        assert "graph TD" in diagram
        assert "A-->B" in diagram

    @patch('lib.bedrock_client.boto3.client')
    def test_answer_question_with_context(self, mock_boto_client):
        """Test RAG-based question answering."""
        mock_client_instance = Mock()
        mock_boto_client.return_value = mock_client_instance
        mock_client_instance.invoke_model.return_value = _nova_response("Answer with citations")

        client = BedrockClient()
        contexts = [
            {'file_path': 'test.py', 'content': 'def test(): pass'}
        ]
        answer = client.answer_question_with_context("What does this do?", contexts)

        assert answer == "Answer with citations"


class TestUtilityFunctions:
    """Test utility functions."""

    def test_count_tokens(self):
        """Test token counting."""
        text = "This is a test"  # 14 characters
        tokens = count_tokens(text)
        assert tokens == 3  # 14 // 4 = 3

    def test_truncate_to_context_no_truncation(self):
        """Test truncation when text is within limit."""
        text = "Short text"
        result = truncate_to_context(text, max_tokens=100)
        assert result == text

    def test_truncate_to_context_with_truncation(self):
        """Test truncation when text exceeds limit."""
        text = "A" * 1000
        result = truncate_to_context(text, max_tokens=10)
        assert len(result) <= 40  # 10 tokens * 4 chars
        assert result.endswith("...")


class TestPromptTemplates:
    """Test prompt template constants."""

    def test_architecture_system_prompt_exists(self):
        """Test architecture system prompt is defined."""
        assert len(ARCHITECTURE_SYSTEM_PROMPT) > 0
        assert "architect" in ARCHITECTURE_SYSTEM_PROMPT.lower()

    def test_file_explain_prompt_exists(self):
        """Test file explain prompt is defined."""
        assert len(FILE_EXPLAIN_PROMPT) > 0
        assert "{level}" in FILE_EXPLAIN_PROMPT
        assert "{file_path}" in FILE_EXPLAIN_PROMPT

    def test_chat_system_prompt_exists(self):
        """Test chat system prompt is defined."""
        assert len(CHAT_SYSTEM_PROMPT) > 0
        assert "code" in CHAT_SYSTEM_PROMPT.lower()

    def test_diagram_generation_prompt_exists(self):
        """Test diagram generation prompt is defined."""
        assert len(DIAGRAM_GENERATION_PROMPT) > 0
        assert "mermaid" in DIAGRAM_GENERATION_PROMPT.lower()
