#!/usr/bin/env python3
"""Smoke test for RepositoryProcessor with a Python repo."""

import os
import shutil
from code_processor import RepositoryProcessor


def main():
    print("=" * 60)
    print("RepositoryProcessor Smoke Test (Python Repo)")
    print("=" * 60)
    print()
    
    repo_path = None
    
    try:
        # Initialize processor
        print("1. Initializing RepositoryProcessor...")
        processor = RepositoryProcessor()
        print("✓ Processor initialized")
        print()
        
        # Clone repository
        print("2. Cloning test repository...")
        test_repo_url = "https://github.com/pallets/click"
        print(f"   URL: {test_repo_url}")
        
        repo_path = processor.clone_repository(test_repo_url)
        
        if os.path.exists(repo_path) and os.path.isdir(repo_path):
            print(f"✓ Repository cloned to: {repo_path}")
        else:
            print(f"✗ Clone failed: path does not exist")
            return
        print()
        
        # Discover files
        print("3. Discovering source files...")
        files = processor.discover_files(repo_path)
        print(f"✓ Discovered {len(files)} files")
        
        if files:
            print("   Files found:")
            for f in files[:5]:
                print(f"     - {f['relative_path']} ({f['extension']})")
            if len(files) > 5:
                print(f"     ... and {len(files) - 5} more")
        print()
        
        # Test file processing
        if files:
            test_file = files[0]
            print(f"4. Processing file: {test_file['relative_path']}")
            print()
            
            # Read content
            print("   4a. Reading file content...")
            with open(test_file['path'], 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            print(f"   ✓ Read {len(content)} characters")
            print()
            
            # Extract imports
            print("   4b. Extracting imports...")
            imports = processor.extract_imports(test_file['path'])
            print(f"   ✓ Found {len(imports)} imports")
            if imports:
                for imp in imports[:5]:
                    print(f"       - {imp}")
                if len(imports) > 5:
                    print(f"       ... and {len(imports) - 5} more")
            print()
            
            # Estimate complexity
            print("   4c. Estimating complexity...")
            complexity = processor.estimate_complexity(test_file['path'])
            print(f"   ✓ Complexity metrics:")
            print(f"       Total lines: {complexity['total_lines']}")
            print(f"       Code lines: {complexity['code_lines']}")
            print(f"       Comment lines: {complexity['comment_lines']}")
            print(f"       Function count: {complexity['function_count']}")
            print(f"       Class count: {complexity['class_count']}")
            print(f"       Complexity: {complexity['estimated_complexity']}")
            print()
            
            # Semantic chunking
            print("   4d. Performing semantic chunking...")
            chunks = processor.semantic_chunking(test_file['path'], content)
            print(f"   ✓ Produced {len(chunks)} chunks")
            
            if chunks:
                chunk_types = {}
                for chunk in chunks:
                    chunk_type = chunk.get('type', 'unknown')
                    chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
                
                print("   Chunk types:")
                for chunk_type, count in chunk_types.items():
                    print(f"       - {chunk_type}: {count}")
                
                print(f"   First chunk preview:")
                first_chunk = chunks[0]
                print(f"       Lines: {first_chunk['start_line']}-{first_chunk['end_line']}")
                print(f"       Type: {first_chunk['type']}")
                preview = first_chunk['content'][:80].replace('\n', ' ')
                print(f"       Content: {preview}...")
            print()
        
        # Detect tech stack
        print("5. Detecting tech stack...")
        tech_stack = processor.detect_tech_stack(files)
        print(f"✓ Tech stack detected:")
        print(f"   Languages: {', '.join(tech_stack['languages']) if tech_stack['languages'] else 'None'}")
        print(f"   Frameworks: {', '.join(tech_stack['frameworks']) if tech_stack['frameworks'] else 'None'}")
        print(f"   Libraries: {', '.join(tech_stack['libraries']) if tech_stack['libraries'] else 'None'}")
        print()
        
        # Build dependency graph
        print("6. Building dependency graph...")
        dep_graph = processor.build_dependency_graph(files)
        print(f"✓ Dependency graph built")
        print(f"   Files with dependencies: {sum(1 for deps in dep_graph.values() if deps)}")
        print(f"   Total dependency edges: {sum(len(deps) for deps in dep_graph.values())}")
        
        if dep_graph:
            files_with_deps = [(f, deps) for f, deps in dep_graph.items() if deps]
            if files_with_deps:
                print("   Sample dependencies:")
                for file_path, deps in files_with_deps[:3]:
                    print(f"       {file_path} -> {deps[:2]}")
        print()
        
        print("=" * 60)
        print("✓ All smoke tests PASSED")
        print("=" * 60)
        print()
        print("Checkpoint 3.2 Status: PASSED")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        print(f"\nCheckpoint 3.2 Status: FAILED")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        if repo_path and os.path.exists(repo_path):
            print(f"\nCleaning up: {repo_path}")
            shutil.rmtree(repo_path, ignore_errors=True)
            print("✓ Cleanup complete")


if __name__ == "__main__":
    main()
