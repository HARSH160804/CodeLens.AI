"""
Documentation Generator - AI-powered documentation creation

Transforms structured architecture analysis data into comprehensive
markdown documentation using AI formatting.
"""

import json
import logging
from typing import Dict, Any
from lib.bedrock_client import BedrockClient

logger = logging.getLogger(__name__)


class GenerationError(Exception):
    """Raised when documentation generation fails."""
    pass


class ValidationError(Exception):
    """Raised when analysis data is incomplete or invalid."""
    pass


class DocumentationGenerator:
    """
    Transform structured analysis data into comprehensive markdown documentation.
    
    Uses AI (Bedrock Claude) for natural language generation and formatting
    while preserving all structured data from the analysis.
    """
    
    def __init__(self, bedrock_client: BedrockClient = None):
        """
        Initialize DocumentationGenerator.
        
        Args:
            bedrock_client: Bedrock client for AI generation (optional)
        """
        self.bedrock_client = bedrock_client or BedrockClient()
    
    def _validate_analysis_data(self, analysis_data: Dict[str, Any]) -> None:
        """
        Validate that analysis data contains required fields.
        
        Args:
            analysis_data: Architecture analysis data
            
        Raises:
            ValidationError: If required fields are missing
        """
        required_fields = [
            'repo_id', 'patterns', 'layers', 'tech_stack',
            'data_flows', 'dependencies', 'metrics', 'recommendations'
        ]
        
        missing_fields = [f for f in required_fields if f not in analysis_data]
        
        if missing_fields:
            raise ValidationError(
                f"Analysis data missing required fields: {', '.join(missing_fields)}"
            )
    
    def _build_prompt(self, analysis_data: Dict[str, Any]) -> str:
        """
        Build structured prompt for AI documentation generation.
        
        Args:
            analysis_data: Complete architecture analysis data
            
        Returns:
            Formatted prompt string
        """
        # Serialize analysis data to JSON for the prompt
        analysis_json = json.dumps(analysis_data, indent=2, default=str)
        
        prompt = f"""You are a technical documentation writer creating comprehensive repository documentation.

INPUT DATA:
{analysis_json}

TASK:
Generate complete technical documentation in markdown format with the following sections:

1. **Overview** - Summarize the repository purpose and architecture (2-3 paragraphs)
2. **Architecture Patterns** - Describe detected patterns with confidence scores and evidence
3. **Layers and Components** - Detail each architectural layer and its components
4. **Technology Stack** - List all technologies with versions, categories, and any vulnerabilities
5. **Data Flows** - Describe data flow scenarios with step-by-step explanations
6. **Dependencies** - Analyze dependency tree, circular dependencies, outdated packages, and vulnerabilities
7. **Quality Metrics** - Present health scores, complexity metrics, hotspots, and technical debt
8. **Recommendations** - List prioritized improvement recommendations with effort estimates

CONSTRAINTS:
- Use ONLY the provided data - do not infer or add external information
- Include Mermaid diagrams from the visualizations field where available
- Use valid markdown syntax with proper headings, lists, code blocks, and tables
- Be comprehensive but concise - focus on actionable insights
- Format code blocks with appropriate language tags
- Use tables for structured data where appropriate
- Include confidence scores and metrics with their actual values

OUTPUT FORMAT:
Start with "# Repository Documentation" as the main heading.
Use ## for section headings and ### for subsections.
End with a footer showing the generation timestamp.

Generate the documentation now:"""
        
        return prompt
    
    def _validate_markdown(self, markdown: str) -> bool:
        """
        Validate that generated markdown contains required sections.
        
        Args:
            markdown: Generated markdown content
            
        Returns:
            True if valid, False otherwise
        """
        required_sections = [
            "## Overview",
            "## Architecture Patterns",
            "## Layers and Components",
            "## Technology Stack",
            "## Data Flows",
            "## Dependencies",
            "## Quality Metrics",
            "## Recommendations"
        ]
        
        for section in required_sections:
            if section not in markdown:
                logger.warning(f"Missing required section: {section}")
                return False
        
        return True
    
    async def generate(self, analysis_data: Dict[str, Any]) -> str:
        """
        Generate markdown documentation from analysis data.
        
        Args:
            analysis_data: Complete ArchitectureAnalysis JSON from AnalysisEngine
            
        Returns:
            Formatted markdown string
            
        Raises:
            GenerationError: If AI generation fails
            ValidationError: If analysis_data is incomplete
        """
        try:
            # Validate input data
            self._validate_analysis_data(analysis_data)
            
            # Build prompt
            prompt = self._build_prompt(analysis_data)
            
            # Call Bedrock for generation
            logger.info(f"Generating documentation for repo {analysis_data.get('repo_id')}")
            
            markdown = self.bedrock_client.invoke_claude(
                prompt=prompt,
                max_tokens=10000,  # Max allowed is 10240, using 10000 for safety
                temperature=0.3,   # Lower temperature for more consistent output
                system_prompt="You are a technical documentation expert who creates clear, comprehensive, and well-structured documentation."
            )
            
            if not markdown:
                raise GenerationError("AI generated empty documentation")
            
            # Validate output
            if not self._validate_markdown(markdown):
                logger.warning("Generated documentation missing some sections, but proceeding")
            
            logger.info(f"Successfully generated documentation ({len(markdown)} chars)")
            return markdown
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Documentation generation failed: {e}", exc_info=True)
            raise GenerationError(f"Failed to generate documentation: {str(e)}")
