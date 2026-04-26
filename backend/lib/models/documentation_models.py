"""
Data models for Documentation Generation and Export Workflow

Defines the data structures for storing and managing generated documentation.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DocumentationRecord:
    """
    Documentation record stored in DynamoDB.
    
    Represents a generated documentation for a repository with metadata
    for state management and retrieval.
    """
    repo_id: str
    content: str
    content_hash: str
    generation_state: str  # not_generated|generating|generated|failed
    created_at: str  # ISO 8601 timestamp
    updated_at: str  # ISO 8601 timestamp
    error_message: Optional[str] = None
    content_s3_key: Optional[str] = None  # For large documents (>400KB)
