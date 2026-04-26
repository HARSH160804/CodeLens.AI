#!/usr/bin/env python3
"""
Check the actual state in DynamoDB for a repository
"""

import boto3
import sys

def check_state(repo_id):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('BloomWay-RepoDocumentation')
    
    try:
        response = table.get_item(Key={'repo_id': repo_id})
        
        if 'Item' in response:
            item = response['Item']
            print(f"✓ Found documentation record for {repo_id}")
            print(f"  State: {item.get('generation_state', 'N/A')}")
            print(f"  Created: {item.get('created_at', 'N/A')}")
            print(f"  Updated: {item.get('updated_at', 'N/A')}")
            print(f"  Has content: {'content' in item}")
            print(f"  Has S3 key: {'content_s3_key' in item}")
            print(f"  Error: {item.get('error_message', 'None')}")
            print(f"\nFull item:")
            for key, value in item.items():
                if key != 'content':  # Don't print full content
                    print(f"  {key}: {value}")
        else:
            print(f"✗ No documentation record found for {repo_id}")
            
    except Exception as e:
        print(f"✗ Error checking state: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_dynamodb_state.py <repo_id>")
        sys.exit(1)
    
    repo_id = sys.argv[1]
    check_state(repo_id)
