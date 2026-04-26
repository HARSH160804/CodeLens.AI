"""
Pattern Detector for Architecture Analysis

Detects architectural patterns with confidence scoring using AI analysis.
"""

import json
import logging
from typing import List, Dict, Any

from bedrock_client import BedrockClient
from models.architecture_models import DetectedPattern

logger = logging.getLogger(__name__)


class PatternDetector:
    """Detects architectural patterns in codebases with confidence scoring."""
    
    SUPPORTED_PATTERNS = [
        'Layered',
        'MVC',
        'Microservices',
        'Event-Driven',
        'CQRS',
        'Clean Architecture',
        'Hexagonal',
        'Monolithic'
    ]
    
    def __init__(self, bedrock_client: BedrockClient = None):
        """
        Initialize pattern detector.
        
        Args:
            bedrock_client: Optional Bedrock client for AI analysis
        """
        self.bedrock_client = bedrock_client or BedrockClient()
    
    def detect_patterns(
        self,
        context: Dict[str, Any]
    ) -> List[DetectedPattern]:
        """
        Detect architectural patterns in codebase.
        
        Args:
            context: Analysis context with repo metadata and file summaries
            
        Returns:
            List of detected patterns with confidence >= 0.5
        """
        try:
            # Build prompt for pattern detection
            prompt = self._build_detection_prompt(context)
            
            # Get AI analysis
            response = self.bedrock_client.invoke_claude(prompt)
            
            # Parse response
            patterns = self._parse_pattern_response(response)
            
            # Filter by confidence threshold
            filtered_patterns = [p for p in patterns if p.confidence >= 0.5]
            
            logger.info(f"Detected {len(filtered_patterns)} patterns with confidence >= 0.5")
            return filtered_patterns
            
        except Exception as e:
            logger.error(f"Error detecting patterns: {str(e)}")
            # Return fallback heuristic-based detection
            return self._fallback_pattern_detection(context)
    
    def _build_detection_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for Bedrock AI pattern detection."""
        file_summaries = context.get('file_summaries', [])
        repo_metadata = context.get('repo_metadata', {})
        
        # Extract file structure
        file_paths = [f.get('file_path', '') for f in file_summaries[:100]]  # Limit to 100 files
        
        prompt = f"""Analyze this codebase structure and detect architectural patterns.

Repository: {repo_metadata.get('name', 'Unknown')}
Primary Language: {repo_metadata.get('primary_language', 'Unknown')}
Total Files: {len(file_summaries)}

File Structure (sample):
{chr(10).join(file_paths[:50])}

Supported Patterns:
{', '.join(self.SUPPORTED_PATTERNS)}

For each detected pattern, provide:
1. Pattern name (must be from supported list)
2. Confidence score (0.0 to 1.0)
3. Evidence files (specific file paths that support this pattern)
4. Description (brief explanation)
5. Pros (list of advantages)
6. Cons (list of disadvantages)
7. Alternatives (list of alternative patterns)

Return ONLY a JSON array of patterns in this exact format:
[
  {{
    "name": "Pattern Name",
    "confidence": 0.85,
    "evidence_files": ["path/to/file1", "path/to/file2"],
    "description": "Brief description",
    "pros": ["Pro 1", "Pro 2"],
    "cons": ["Con 1", "Con 2"],
    "alternatives": ["Alternative 1", "Alternative 2"]
  }}
]

Only include patterns with confidence >= 0.5. Return empty array [] if no patterns detected."""
        
        return prompt
    
    def _parse_pattern_response(self, response: str) -> List[DetectedPattern]:
        """Parse AI response into DetectedPattern objects."""
        try:
            # Extract JSON from response
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                logger.warning("No JSON array found in response")
                return []
            
            json_str = response[json_start:json_end]
            patterns_data = json.loads(json_str)
            
            patterns = []
            for data in patterns_data:
                # Validate pattern name
                if data.get('name') not in self.SUPPORTED_PATTERNS:
                    logger.warning(f"Unsupported pattern name: {data.get('name')}")
                    continue
                
                pattern = DetectedPattern(
                    name=data['name'],
                    confidence=float(data['confidence']),
                    evidence_files=data.get('evidence_files', []),
                    description=data.get('description', ''),
                    pros=data.get('pros', []),
                    cons=data.get('cons', []),
                    alternatives=data.get('alternatives', [])
                )
                patterns.append(pattern)
            
            return patterns
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error parsing pattern response: {str(e)}")
            return []
    
    def _fallback_pattern_detection(self, context: Dict[str, Any]) -> List[DetectedPattern]:
        """
        Fallback heuristic-based pattern detection when AI fails.
        
        Uses simple file structure analysis to detect common patterns.
        """
        file_summaries = context.get('file_summaries', [])
        file_paths = [f.get('file_path', '').lower() for f in file_summaries]
        
        patterns = []
        
        # Check for MVC pattern
        has_models = any('model' in path for path in file_paths)
        has_views = any('view' in path for path in file_paths)
        has_controllers = any('controller' in path for path in file_paths)
        
        if has_models and has_views and has_controllers:
            patterns.append(DetectedPattern(
                name='MVC',
                confidence=0.7,
                evidence_files=[p for p in file_paths if any(x in p for x in ['model', 'view', 'controller'])][:5],
                description='MVC pattern detected based on file structure',
                pros=['Clear separation of concerns', 'Well-understood pattern'],
                cons=['Can lead to fat controllers', 'Tight coupling'],
                alternatives=['Clean Architecture', 'Hexagonal']
            ))
        
        # Check for Layered pattern
        has_layers = sum([
            any('handler' in path or 'controller' in path for path in file_paths),
            any('service' in path or 'business' in path for path in file_paths),
            any('repository' in path or 'dao' in path for path in file_paths)
        ])
        
        if has_layers >= 2:
            patterns.append(DetectedPattern(
                name='Layered',
                confidence=0.6,
                evidence_files=[p for p in file_paths if any(x in p for x in ['handler', 'service', 'repository'])][:5],
                description='Layered architecture detected based on file organization',
                pros=['Clear separation', 'Easy to understand'],
                cons=['Can become rigid', 'Layer coupling'],
                alternatives=['Hexagonal', 'Clean Architecture']
            ))
        
        # Check for Microservices (multiple service directories)
        service_dirs = set()
        for path in file_paths:
            if 'service' in path:
                parts = path.split('/')
                if 'service' in parts:
                    idx = parts.index('service')
                    if idx + 1 < len(parts):
                        service_dirs.add(parts[idx + 1])
        
        if len(service_dirs) >= 3:
            patterns.append(DetectedPattern(
                name='Microservices',
                confidence=0.55,
                evidence_files=list(service_dirs)[:5],
                description='Multiple service directories suggest microservices architecture',
                pros=['Independent deployment', 'Scalability'],
                cons=['Complexity', 'Distributed system challenges'],
                alternatives=['Monolithic', 'Modular Monolith']
            ))
        
        logger.info(f"Fallback detection found {len(patterns)} patterns")
        return patterns
    
    def _calculate_confidence(self, evidence: Dict[str, Any]) -> float:
        """
        Calculate confidence score based on evidence strength.
        
        Args:
            evidence: Evidence data for pattern detection
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # This is a placeholder - actual implementation would analyze evidence
        return 0.75
    
    def _extract_evidence_files(self, context: Dict[str, Any], pattern_name: str) -> List[str]:
        """
        Identify supporting files for a pattern.
        
        Args:
            context: Analysis context
            pattern_name: Name of the pattern
            
        Returns:
            List of file paths that support the pattern
        """
        # This is a placeholder - actual implementation would extract relevant files
        return []
    
    def _get_pattern_metadata(self, pattern_name: str) -> Dict[str, Any]:
        """
        Retrieve pros/cons/alternatives for a pattern.
        
        Args:
            pattern_name: Name of the pattern
            
        Returns:
            Dictionary with pros, cons, and alternatives
        """
        # Pattern metadata lookup
        metadata = {
            'MVC': {
                'pros': ['Clear separation of concerns', 'Well-understood pattern', 'Easy to test'],
                'cons': ['Can lead to fat controllers', 'Tight coupling between layers'],
                'alternatives': ['MVVM', 'Clean Architecture', 'Hexagonal']
            },
            'Layered': {
                'pros': ['Clear separation', 'Easy to understand', 'Good for traditional apps'],
                'cons': ['Can become rigid', 'Layer coupling', 'May not scale well'],
                'alternatives': ['Hexagonal', 'Clean Architecture', 'Microservices']
            },
            'Microservices': {
                'pros': ['Independent deployment', 'Scalability', 'Technology diversity'],
                'cons': ['Complexity', 'Distributed system challenges', 'Network overhead'],
                'alternatives': ['Monolithic', 'Modular Monolith', 'Service-Oriented']
            },
            'Event-Driven': {
                'pros': ['Loose coupling', 'Scalability', 'Asynchronous processing'],
                'cons': ['Complexity', 'Debugging challenges', 'Eventual consistency'],
                'alternatives': ['Request-Response', 'CQRS', 'Microservices']
            },
            'CQRS': {
                'pros': ['Optimized reads/writes', 'Scalability', 'Clear separation'],
                'cons': ['Complexity', 'Eventual consistency', 'More code'],
                'alternatives': ['Traditional CRUD', 'Event Sourcing', 'Microservices']
            },
            'Clean Architecture': {
                'pros': ['Independence', 'Testability', 'Flexibility'],
                'cons': ['Learning curve', 'More boilerplate', 'Over-engineering risk'],
                'alternatives': ['Hexagonal', 'Layered', 'MVC']
            },
            'Hexagonal': {
                'pros': ['Port and adapters', 'Testability', 'Technology independence'],
                'cons': ['Complexity', 'More abstractions', 'Learning curve'],
                'alternatives': ['Clean Architecture', 'Layered', 'Onion']
            },
            'Monolithic': {
                'pros': ['Simplicity', 'Easy deployment', 'Good for small apps'],
                'cons': ['Scaling challenges', 'Tight coupling', 'Long build times'],
                'alternatives': ['Microservices', 'Modular Monolith', 'Service-Oriented']
            }
        }
        
        return metadata.get(pattern_name, {
            'pros': [],
            'cons': [],
            'alternatives': []
        })
