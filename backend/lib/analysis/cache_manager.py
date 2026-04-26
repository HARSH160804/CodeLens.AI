"""
Cache Manager for Architecture Analysis

Manages DynamoDB caching with 24-hour TTL for architecture analysis results.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching of architecture analysis results in DynamoDB."""
    
    TTL_HOURS = 24
    
    def __init__(self):
        """Initialize the cache manager with DynamoDB client."""
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = os.environ.get('CACHE_TABLE_NAME', 'architecture-analysis-cache')
        try:
            self.table = self.dynamodb.Table(self.table_name)
        except Exception as e:
            logger.error(f"Failed to initialize cache table: {str(e)}")
            self.table = None
    
    def get_cached_analysis(
        self,
        repo_id: str,
        level: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached analysis if valid.
        
        Args:
            repo_id: Repository identifier
            level: Analysis level (basic/intermediate/advanced)
            
        Returns:
            Cached analysis data if valid, None otherwise
        """
        if not self.table:
            logger.warning("Cache table not available")
            return None
        
        cache_key = self._generate_cache_key(repo_id, level)
        
        try:
            response = self.table.get_item(Key={'cache_key': cache_key})
            
            if 'Item' not in response:
                logger.info(f"Cache miss for key: {cache_key}")
                return None
            
            item = response['Item']
            
            # Check if cache is still valid
            if not self._is_cache_valid(item):
                logger.info(f"Cache expired for key: {cache_key}")
                return None
            
            logger.info(f"Cache hit for key: {cache_key}")
            return json.loads(item['data'])
            
        except ClientError as e:
            logger.error(f"Error retrieving from cache: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving from cache: {str(e)}")
            return None
    
    def cache_analysis(
        self,
        repo_id: str,
        level: str,
        analysis: Dict[str, Any]
    ) -> None:
        """
        Store analysis with TTL.
        
        Args:
            repo_id: Repository identifier
            level: Analysis level
            analysis: Analysis data to cache
        """
        if not self.table:
            logger.warning("Cache table not available, skipping cache write")
            return
        
        cache_key = self._generate_cache_key(repo_id, level)
        ttl = int((datetime.utcnow() + timedelta(hours=self.TTL_HOURS)).timestamp())
        
        try:
            self.table.put_item(
                Item={
                    'cache_key': cache_key,
                    'data': json.dumps(analysis),
                    'ttl': ttl,
                    'created_at': datetime.utcnow().isoformat(),
                    'repo_id': repo_id,
                    'level': level
                }
            )
            logger.info(f"Cached analysis for key: {cache_key} with TTL: {ttl}")
            
        except ClientError as e:
            logger.error(f"Error writing to cache: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error writing to cache: {str(e)}")
    
    def _generate_cache_key(self, repo_id: str, level: str) -> str:
        """
        Create composite cache key.
        
        Args:
            repo_id: Repository identifier
            level: Analysis level
            
        Returns:
            Cache key in format: {repo_id}#{level}
        """
        return f"{repo_id}#{level}"
    
    def _is_cache_valid(self, item: Dict[str, Any]) -> bool:
        """
        Check TTL expiration.
        
        Args:
            item: DynamoDB item
            
        Returns:
            True if cache is still valid, False if expired
        """
        if 'ttl' not in item:
            return False
        
        ttl = int(item['ttl'])
        current_time = int(datetime.utcnow().timestamp())
        
        return current_time < ttl
