#!/usr/bin/env python3
"""
Clear Architecture Cache Script

Clears the cached architecture analysis for a specific repository
so you can test the new Analysis Engine v2.0 immediately after deployment.

Usage:
    python3 clear_architecture_cache.py <repo_id>
    
Example:
    python3 clear_architecture_cache.py e914711e-5d3c-47c4-a3cb-149145332521
"""

import sys
import boto3
from botocore.exceptions import ClientError

def clear_cache(repo_id: str):
    """Clear architecture cache for all levels of a repository."""
    
    # Initialize DynamoDB
    dynamodb = boto3.resource('dynamodb')
    cache_table = dynamodb.Table('BloomWay-Cache')
    
    levels = ['basic', 'intermediate', 'advanced']
    cleared = []
    not_found = []
    
    print(f"Clearing architecture cache for repo: {repo_id}")
    print("-" * 60)
    
    for level in levels:
        cache_key = f"{repo_id}#{level}"
        
        try:
            # Delete the cache entry
            response = cache_table.delete_item(
                Key={'cache_key': cache_key},
                ReturnValues='ALL_OLD'
            )
            
            if 'Attributes' in response:
                cleared.append(level)
                print(f"✓ Cleared cache for level: {level}")
            else:
                not_found.append(level)
                print(f"○ No cache found for level: {level}")
                
        except ClientError as e:
            print(f"✗ Error clearing cache for {level}: {str(e)}")
    
    print("-" * 60)
    print(f"\nSummary:")
    print(f"  Cleared: {len(cleared)} levels")
    print(f"  Not found: {len(not_found)} levels")
    
    if cleared:
        print(f"\n✓ Cache cleared successfully!")
        print(f"  You can now reload the architecture page to see the new analysis.")
    else:
        print(f"\n○ No cache entries were found (may already be cleared)")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 clear_architecture_cache.py <repo_id>")
        print("\nExample:")
        print("  python3 clear_architecture_cache.py e914711e-5d3c-47c4-a3cb-149145332521")
        sys.exit(1)
    
    repo_id = sys.argv[1]
    
    try:
        clear_cache(repo_id)
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        sys.exit(1)
