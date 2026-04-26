"""
Example usage of BedrockClient.

This script demonstrates how to use the BedrockClient for various tasks.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.bedrock_client import BedrockClient, count_tokens, truncate_to_context


def example_embedding():
    """Example: Generate embeddings for code snippets."""
    print("=" * 60)
    print("Example 1: Generate Embeddings")
    print("=" * 60)
    
    client = BedrockClient()
    
    code_snippet = """
    def calculate_fibonacci(n):
        if n <= 1:
            return n
        return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
    """
    
    print(f"Code snippet:\n{code_snippet}")
    print("\nGenerating embedding...")
    
    try:
        embedding = client.generate_embedding(code_snippet)
        print(f"✓ Embedding generated: {len(embedding)} dimensions")
        print(f"  First 5 values: {embedding[:5]}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print()


def example_architecture_analysis():
    """Example: Analyze repository architecture."""
    print("=" * 60)
    print("Example 2: Architecture Analysis")
    print("=" * 60)
    
    client = BedrockClient()
    
    repo_structure = """
    project/
    ├── src/
    │   ├── controllers/
    │   │   ├── user_controller.py
    │   │   └── auth_controller.py
    │   ├── models/
    │   │   ├── user.py
    │   │   └── session.py
    │   ├── views/
    │   │   └── templates/
    │   └── app.py
    ├── tests/
    └── requirements.txt
    """
    
    print(f"Repository structure:\n{repo_structure}")
    print("\nAnalyzing architecture...")
    
    try:
        summary = client.generate_architecture_summary(repo_structure)
        print(f"✓ Architecture Summary:\n{summary}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print()


def example_file_explanation():
    """Example: Explain code file at different levels."""
    print("=" * 60)
    print("Example 3: File Explanation")
    print("=" * 60)
    
    client = BedrockClient()
    
    code_content = """
    class UserRepository:
        def __init__(self, db_connection):
            self.db = db_connection
        
        def find_by_id(self, user_id):
            return self.db.query("SELECT * FROM users WHERE id = ?", user_id)
        
        def save(self, user):
            if user.id:
                return self.db.execute("UPDATE users SET name = ? WHERE id = ?", 
                                      user.name, user.id)
            else:
                return self.db.execute("INSERT INTO users (name) VALUES (?)", 
                                      user.name)
    """
    
    print(f"Code:\n{code_content}")
    
    for level in ['beginner', 'intermediate', 'advanced']:
        print(f"\n--- {level.upper()} Level Explanation ---")
        try:
            explanation = client.explain_file(
                file_path="repositories/user_repository.py",
                code_content=code_content,
                level=level
            )
            print(explanation)
        except Exception as e:
            print(f"✗ Error: {e}")
    
    print()


def example_mermaid_diagram():
    """Example: Generate Mermaid diagram."""
    print("=" * 60)
    print("Example 4: Mermaid Diagram Generation")
    print("=" * 60)
    
    client = BedrockClient()
    
    architecture_summary = """
    This is a microservices architecture with:
    - API Gateway handling incoming requests
    - User Service managing user data
    - Auth Service handling authentication
    - Database for persistence
    - Message Queue for async communication
    """
    
    print(f"Architecture Summary:\n{architecture_summary}")
    print("\nGenerating Mermaid diagram...")
    
    try:
        diagram = client.generate_mermaid_diagram(architecture_summary)
        print(f"✓ Mermaid Diagram:\n```mermaid\n{diagram}\n```")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print()


def example_rag_chat():
    """Example: RAG-based question answering."""
    print("=" * 60)
    print("Example 5: RAG-based Chat")
    print("=" * 60)
    
    client = BedrockClient()
    
    code_contexts = [
        {
            'file_path': 'src/auth.py',
            'content': '''
def authenticate_user(username, password):
    user = User.find_by_username(username)
    if user and user.verify_password(password):
        return create_session(user)
    return None
'''
        },
        {
            'file_path': 'src/models/user.py',
            'content': '''
class User:
    def verify_password(self, password):
        return bcrypt.checkpw(password.encode(), self.password_hash)
'''
        }
    ]
    
    question = "How does the authentication system work?"
    
    print(f"Question: {question}\n")
    print("Code Context:")
    for ctx in code_contexts:
        print(f"  - {ctx['file_path']}")
    
    print("\nGenerating answer...")
    
    try:
        answer = client.answer_question_with_context(question, code_contexts)
        print(f"✓ Answer:\n{answer}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print()


def example_streaming():
    """Example: Streaming response."""
    print("=" * 60)
    print("Example 6: Streaming Response")
    print("=" * 60)
    
    client = BedrockClient()
    
    prompt = "Explain the benefits of microservices architecture in 3 sentences."
    
    print(f"Prompt: {prompt}\n")
    print("Streaming response:")
    
    try:
        for chunk in client.invoke_claude_streaming(prompt, max_tokens=200):
            print(chunk, end='', flush=True)
        print("\n✓ Streaming complete")
    except Exception as e:
        print(f"\n✗ Error: {e}")
    
    print()


def example_token_utilities():
    """Example: Token counting and truncation."""
    print("=" * 60)
    print("Example 7: Token Utilities")
    print("=" * 60)
    
    text = "This is a sample text. " * 100  # Long text
    
    print(f"Original text length: {len(text)} characters")
    
    token_count = count_tokens(text)
    print(f"Estimated tokens: {token_count}")
    
    truncated = truncate_to_context(text, max_tokens=50)
    print(f"Truncated text length: {len(truncated)} characters")
    print(f"Truncated text: {truncated[:100]}...")
    
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("BedrockClient Usage Examples")
    print("=" * 60 + "\n")
    
    examples = [
        ("Embeddings", example_embedding),
        ("Architecture Analysis", example_architecture_analysis),
        ("File Explanation", example_file_explanation),
        ("Mermaid Diagram", example_mermaid_diagram),
        ("RAG Chat", example_rag_chat),
        ("Streaming", example_streaming),
        ("Token Utilities", example_token_utilities),
    ]
    
    print("Available examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    print("\nRunning all examples...\n")
    
    for name, example_func in examples:
        try:
            example_func()
        except KeyboardInterrupt:
            print("\n\nExamples interrupted by user.")
            break
        except Exception as e:
            print(f"✗ Example '{name}' failed: {e}\n")
    
    print("=" * 60)
    print("Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
