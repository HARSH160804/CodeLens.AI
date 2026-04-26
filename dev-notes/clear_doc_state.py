#!/usr/bin/env python3
"""
Clear/reset documentation state for a repository
"""

import boto3
import sys

def clear_state(repo_id):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('BloomWay-RepoDocumentation')
    
    try:
        # Delete the item
        table.delete_item(Key={'repo_id': repo_id})
        print(f"✓ Cleared documentation state for {repo_id}")
        print(f"  You can now try generating documentation again")
            
    except Exception as e:
        print(f"✗ Error clearing state: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python clear_doc_state.py <repo_id>")
        sys.exit(1)
    
    repo_id = sys.argv[1]
    clear_state(repo_id)
