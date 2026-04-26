"""
Unit tests for DocumentationGenerator class.

Tests AI-powered documentation generation and validation.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add backend lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from documentation.generator import DocumentationGenerator, GenerationError, ValidationError


class TestDocumentationGenerator:
    """Test suite for DocumentationGenerator."""
    
    @pytest.fixture
    def mock_bedrock_client(self):
        """Mock Bedrock client."""
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = {
            'content': self._get_sample_markdown()
        }
        return mock_client
    
    @pytest.fixture
    def generator(self, mock_bedrock_client):
        """Create DocumentationGenerator with mocked Bedrock client."""
        return DocumentationGenerator(mock_bedrock_client)
    
    @staticmethod
    def _get_minimal_analysis_data():
        """Get minimal valid analysis data."""
        return {
            'repo_id': 'test-repo-123',
            'patterns': [],
            'layers': [],
            'tech_stack': [],
            'data_flows': [],
            'dependencies': {},
            'metrics': {},
            'recommendations': []
        }
    
    @staticmethod
    def _get_complete_analysis_data():
        """Get complete analysis data with all fields."""
        return {
            'repo_id': 'test-repo-456',
            'schema_version': '2.0',
            'generated_at': '2024-01-01T00:00:00Z',
            'patterns': [
                {
                    'name': 'MVC',
                    'confidence': 0.85,
                    'evidence_files': ['app.py', 'models.py'],
                    'description': 'Model-View-Controller pattern'
                }
            ],
            'layers': [
                {
                    'name': 'presentation',
                    'components': [
                        {
                            'name': 'UserController',
                            'type': 'Controller',
                            'file_path': 'controllers/user.py'
                        }
                    ]
                }
            ],
            'tech_stack': [
                {
                    'name': 'Python',
                    'version': '3.9',
                    'category': 'language'
                }
            ],
            'data_flows': [],
            'dependencies': {
                'circular_dependencies': [],
                'outdated_packages': []
            },
            'metrics': {
                'health_score': 75.5,
                'complexity_metrics': {
                    'average_cyclomatic': 3.2
                }
            },
            'recommendations': [
                {
                    'title': 'Reduce complexity',
                    'priority': 'high',
                    'category': 'refactoring'
                }
            ]
        }
    
    @staticmethod
    def _get_sample_markdown():
        """Get sample generated markdown."""
        return """# Repository Documentation

## Overview
This is a test repository with MVC architecture.

## Architecture Patterns
- MVC (85% confidence)

## Layers and Components
### Presentation Layer
- UserController

## Technology Stack
- Python 3.9

## Data Flows
No data flows detected.

## Dependencies
No circular dependencies found.

## Quality Metrics
Health Score: 75.5/100

## Recommendations
1. Reduce complexity (High priority)
"""
    
    def test_validate_analysis_data_valid(self, generator):
        """Test validation with valid data."""
        data = self._get_minimal_analysis_data()
        
        # Should not raise exception
        generator._validate_analysis_data(data)
    
    def test_validate_analysis_data_missing_fields(self, generator):
        """Test validation with missing required fields."""
        data = {'repo_id': 'test'}  # Missing required fields
        
        with pytest.raises(ValidationError) as exc_info:
            generator._validate_analysis_data(data)
        
        assert 'missing required fields' in str(exc_info.value).lower()
    
    def test_build_prompt_contains_data(self, generator):
        """Test that prompt contains analysis data."""
        data = self._get_complete_analysis_data()
        
        prompt = generator._build_prompt(data)
        
        # Verify prompt contains key elements
        assert 'test-repo-456' in prompt
        assert 'MVC' in prompt
        assert 'Python' in prompt
        assert 'Overview' in prompt
        assert 'Architecture Patterns' in prompt
    
    def test_build_prompt_structure(self, generator):
        """Test prompt has correct structure."""
        data = self._get_minimal_analysis_data()
        
        prompt = generator._build_prompt(data)
        
        # Verify prompt structure
        assert 'INPUT DATA:' in prompt
        assert 'TASK:' in prompt
        assert 'CONSTRAINTS:' in prompt
        assert 'OUTPUT FORMAT:' in prompt
    
    def test_validate_markdown_valid(self, generator):
        """Test markdown validation with valid content."""
        markdown = self._get_sample_markdown()
        
        is_valid = generator._validate_markdown(markdown)
        
        assert is_valid is True
    
    def test_validate_markdown_missing_sections(self, generator):
        """Test markdown validation with missing sections."""
        markdown = """# Repository Documentation

## Overview
Just an overview, missing other sections.
"""
        
        is_valid = generator._validate_markdown(markdown)
        
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_generate_success(self, generator, mock_bedrock_client):
        """Test successful documentation generation."""
        data = self._get_complete_analysis_data()
        
        markdown = await generator.generate(data)
        
        # Verify Bedrock was called
        mock_bedrock_client.invoke_model.assert_called_once()
        call_args = mock_bedrock_client.invoke_model.call_args[1]
        assert 'prompt' in call_args
        assert 'max_tokens' in call_args
        
        # Verify output
        assert markdown is not None
        assert len(markdown) > 0
        assert '# Repository Documentation' in markdown
    
    @pytest.mark.asyncio
    async def test_generate_with_minimal_data(self, generator, mock_bedrock_client):
        """Test generation with minimal analysis data."""
        data = self._get_minimal_analysis_data()
        
        markdown = await generator.generate(data)
        
        assert markdown is not None
        mock_bedrock_client.invoke_model.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_validation_error(self, generator):
        """Test generation with invalid data."""
        data = {'repo_id': 'test'}  # Missing required fields
        
        with pytest.raises(ValidationError):
            await generator.generate(data)
    
    @pytest.mark.asyncio
    async def test_generate_empty_response(self, generator, mock_bedrock_client):
        """Test generation when AI returns empty response."""
        mock_bedrock_client.invoke_model.return_value = {'content': ''}
        data = self._get_minimal_analysis_data()
        
        with pytest.raises(GenerationError) as exc_info:
            await generator.generate(data)
        
        assert 'empty documentation' in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_generate_bedrock_error(self, generator, mock_bedrock_client):
        """Test generation when Bedrock fails."""
        mock_bedrock_client.invoke_model.side_effect = Exception("Bedrock API error")
        data = self._get_minimal_analysis_data()
        
        with pytest.raises(GenerationError) as exc_info:
            await generator.generate(data)
        
        assert 'failed to generate' in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_generate_with_special_characters(self, generator, mock_bedrock_client):
        """Test generation with special characters in data."""
        data = self._get_minimal_analysis_data()
        data['patterns'] = [
            {
                'name': 'Test "Pattern" with <special> & chars',
                'confidence': 0.9,
                'evidence_files': ['file.py']
            }
        ]
        
        markdown = await generator.generate(data)
        
        # Should handle special characters without error
        assert markdown is not None
        mock_bedrock_client.invoke_model.assert_called_once()
    
    def test_prompt_includes_all_sections(self, generator):
        """Test that prompt requests all required sections."""
        data = self._get_minimal_analysis_data()
        
        prompt = generator._build_prompt(data)
        
        required_sections = [
            'Overview',
            'Architecture Patterns',
            'Layers and Components',
            'Technology Stack',
            'Data Flows',
            'Dependencies',
            'Quality Metrics',
            'Recommendations'
        ]
        
        for section in required_sections:
            assert section in prompt


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
