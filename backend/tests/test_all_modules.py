"""
Comprehensive test suite for BloomWay-Ai backend.
Covers: complexity_analyzer, static_analysis, metadata endpoint,
        architecture endpoint schema, explain endpoint schema, caching logic.

Uses moto to mock DynamoDB and unittest.mock to patch Bedrock.
"""
import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import datetime, timedelta

import boto3
from moto import mock_aws

# ── Path setup ──────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'handlers'))


# =====================================================================
#  1. complexity_analyzer tests
# =====================================================================
from complexity_analyzer import compute_complexity


class TestComputeComplexity:
    """Tests for the deterministic complexity analyzer."""

    def test_empty_code(self):
        result = compute_complexity("")
        assert result['score'] >= 1
        assert result['metrics']['total_lines'] == 1  # empty string → one empty line
        assert result['metrics']['function_count'] == 0

    def test_simple_function(self):
        code = "def hello():\n    print('hi')\n"
        result = compute_complexity(code)
        assert result['metrics']['function_count'] == 1
        assert result['metrics']['class_count'] == 0
        assert 1 <= result['score'] <= 10

    def test_class_detection(self):
        code = "class Foo:\n    def bar(self):\n        pass\n"
        result = compute_complexity(code)
        assert result['metrics']['class_count'] == 1
        assert result['metrics']['function_count'] >= 1

    def test_async_detection(self):
        code = "async def fetch():\n    await get_data()\n"
        result = compute_complexity(code)
        assert result['metrics']['async_count'] >= 1

    def test_try_catch_counting(self):
        code = (
            "try:\n    risky()\nexcept ValueError:\n    pass\n"
            "except Exception:\n    pass\n"
        )
        result = compute_complexity(code)
        assert result['metrics']['try_catch_count'] == 3  # 1 try + 2 except

    def test_deep_nesting(self):
        code = "if True:\n    if True:\n        if True:\n            if True:\n                x = 1\n"
        result = compute_complexity(code)
        assert result['metrics']['nesting_estimate'] >= 1

    def test_score_range(self):
        """Score must always be 1-10."""
        for code in ["", "x = 1", "def f():\n" * 50]:
            result = compute_complexity(code)
            assert 1 <= result['score'] <= 10

    def test_complex_file_higher_score(self):
        simple = "x = 1\n"
        complex_code = "\n".join([
            "class Service:",
            "    async def process(self, data):",
            "        try:",
            "            for item in data:",
            "                if item.get('active'):",
            "                    for sub in item['children']:",
            "                        if sub.get('valid'):",
            "                            await self._transform(sub)",
            "        except Exception as e:",
            "            raise",
        ] * 5)
        simple_score = compute_complexity(simple)['score']
        complex_score = compute_complexity(complex_code)['score']
        assert complex_score >= simple_score


# =====================================================================
#  2. static_analysis tests
# =====================================================================
from static_analysis import analyze_file_metadata


class TestStaticAnalysis:
    """Tests for the regex-based static analysis module."""

    def test_python_imports(self):
        code = "import os\nfrom datetime import datetime\n"
        result = analyze_file_metadata(code)
        assert 'os' in result['imports']
        assert 'datetime' in result['imports']

    def test_js_imports(self):
        code = "import React from 'react';\nconst fs = require('fs');\n"
        result = analyze_file_metadata(code)
        assert 'react' in result['imports']
        assert 'fs' in result['imports']

    def test_function_names_python(self):
        code = "def foo():\n    pass\nasync def bar():\n    pass\n"
        result = analyze_file_metadata(code)
        assert 'foo' in result['function_names']
        assert 'bar' in result['function_names']

    def test_function_names_js(self):
        code = "function greet() {}\nconst run = async () => {}\n"
        result = analyze_file_metadata(code)
        assert 'greet' in result['function_names']
        assert 'run' in result['function_names']

    def test_class_names(self):
        code = "class MyService:\n    pass\n"
        result = analyze_file_metadata(code)
        assert 'MyService' in result['class_names']

    def test_async_usage(self):
        code = "async def fetch():\n    data = await get()\n"
        result = analyze_file_metadata(code)
        assert any('async' in a for a in result['async_usage'])
        assert any('await' in a for a in result['async_usage'])

    def test_db_keywords(self):
        code = "table.put_item(Item=data)\nresult = table.get_item(Key=k)\n"
        result = analyze_file_metadata(code)
        assert len(result['db_keywords']) >= 1

    def test_api_patterns(self):
        code = "resp = requests.get('https://api.example.com/data')\n"
        result = analyze_file_metadata(code)
        assert len(result['api_patterns']) >= 1

    def test_empty_code(self):
        result = analyze_file_metadata("")
        assert result['imports'] == []
        assert result['function_names'] == []
        assert result['class_names'] == []

    def test_return_structure(self):
        result = analyze_file_metadata("x = 1")
        for key in ['imports', 'function_names', 'class_names',
                     'async_usage', 'db_keywords', 'api_patterns']:
            assert key in result
            assert isinstance(result[key], list)


# =====================================================================
#  Shared DynamoDB fixtures (moto)
# =====================================================================
@pytest.fixture
def aws_env(monkeypatch):
    """Set dummy AWS credentials and table env vars."""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('REPOSITORIES_TABLE', 'BloomWay-Repositories')
    monkeypatch.setenv('CACHE_TABLE', 'BloomWay-Cache')


@pytest.fixture
def dynamodb_tables(aws_env):
    """Create mock DynamoDB tables used by handlers."""
    with mock_aws():
        ddb = boto3.resource('dynamodb', region_name='us-east-1')

        # Repos table
        repos = ddb.create_table(
            TableName='BloomWay-Repositories',
            KeySchema=[{'AttributeName': 'repo_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'repo_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        # Cache table (partition: repo_id, sort: sort_key)
        cache = ddb.create_table(
            TableName='BloomWay-Cache',
            KeySchema=[
                {'AttributeName': 'repo_id', 'KeyType': 'HASH'},
                {'AttributeName': 'sort_key', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'repo_id', 'AttributeType': 'S'},
                {'AttributeName': 'sort_key', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        yield {'repos': repos, 'cache': cache, 'resource': ddb}


def _seed_repo(repos_table, repo_id='test-repo-123'):
    """Insert a sample repo metadata item."""
    repos_table.put_item(Item={
        'repo_id': repo_id,
        'source': 'https://github.com/test/repo',
        'source_type': 'github',
        'status': 'completed',
        'file_count': 42,
        'chunk_count': 150,
        'total_lines_of_code': 8500,
        'language_breakdown': {'.py': 15, '.js': 10, '.ts': 8},
        'primary_language': '.py',
        'folder_depth': 4,
        'largest_file': {'path': 'src/main.py', 'lines': 600},
        'indexed_at': '2026-03-03T12:00:00Z',
        'tech_stack': {
            'languages': ['Python', 'JavaScript'],
            'frameworks': ['Flask', 'React'],
            'libraries': ['boto3']
        },
        'architecture_summary': 'Serverless REST API with React frontend',
        'file_paths': ['src/main.py', 'src/app.tsx', 'requirements.txt'],
        'file_tree': {'name': 'root', 'type': 'directory', 'children': []},
        'created_at': '2026-03-03T12:00:00Z',
        'updated_at': '2026-03-03T12:00:00Z',
    })


# =====================================================================
#  3. GET /repo/{id}/metadata endpoint tests
# =====================================================================
class TestGetRepoMetadata:
    """Tests for the get_repo_metadata handler."""

    def test_returns_stored_metadata(self, dynamodb_tables):
        _seed_repo(dynamodb_tables['repos'])

        # Patch the module-level table reference
        with patch.dict('os.environ', {
            'REPOSITORIES_TABLE': 'BloomWay-Repositories'
        }):
            import importlib
            import get_repo_metadata as mod
            importlib.reload(mod)
            mod.repos_table = dynamodb_tables['repos']

            event = {'pathParameters': {'id': 'test-repo-123'}}
            resp = mod.lambda_handler(event, None)

        assert resp['statusCode'] == 200
        body = json.loads(resp['body'])
        assert body['repoName'] == 'test/repo'
        assert body['totalFiles'] == 42
        assert body['totalLines'] == 8500
        assert body['primaryLanguage'] == '.py'
        assert '.py' in body['languageBreakdown']
        assert body['indexedAt'] == '2026-03-03T12:00:00Z'

    def test_missing_repo_id(self, dynamodb_tables):
        import importlib
        import get_repo_metadata as mod
        importlib.reload(mod)
        mod.repos_table = dynamodb_tables['repos']

        event = {'pathParameters': {}}
        resp = mod.lambda_handler(event, None)
        assert resp['statusCode'] == 400

    def test_repo_not_found(self, dynamodb_tables):
        import importlib
        import get_repo_metadata as mod
        importlib.reload(mod)
        mod.repos_table = dynamodb_tables['repos']

        event = {'pathParameters': {'id': 'nonexistent'}}
        resp = mod.lambda_handler(event, None)
        assert resp['statusCode'] == 404


# =====================================================================
#  4. Architecture endpoint JSON schema tests
# =====================================================================
class TestArchitectureJsonSchema:
    """Validate the architecture handler returns the correct JSON schema."""

    def _make_event(self, repo_id='test-repo-123', level='intermediate'):
        return {
            'pathParameters': {'id': repo_id},
            'queryStringParameters': {'level': level}
        }

    def test_full_schema_returned(self, dynamodb_tables):
        _seed_repo(dynamodb_tables['repos'])

        mock_llm_response = json.dumps({
            'overview': 'Test architecture',
            'architectureStyle': 'Serverless',
            'components': [{'name': 'API', 'description': 'REST API', 'files': ['app.py'], 'role': 'API Layer'}],
            'dataFlowSteps': ['Step 1: Request comes in', 'Step 2: Processed'],
            'mermaidDiagram': 'flowchart TD\n    A[Client] --> B[API]',
            'confidence': 0.85
        })

        with patch.dict('os.environ', {
            'REPOSITORIES_TABLE': 'BloomWay-Repositories',
            'CACHE_TABLE': 'BloomWay-Cache',
        }):
            import importlib
            import architecture as mod
            importlib.reload(mod)
            mod.repos_table = dynamodb_tables['repos']
            mod.cache_table = dynamodb_tables['cache']
            mod.bedrock_client = MagicMock()
            mod.bedrock_client.invoke_claude.return_value = mock_llm_response
            mod.bedrock_client.ARCHITECTURE_SYSTEM_PROMPT = 'You are an architect.'
            mod.vector_store = MagicMock()
            mod.vector_store.search.return_value = []

            resp = mod.lambda_handler(self._make_event(), None)

        assert resp['statusCode'] == 200
        body = json.loads(resp['body'])

        # Validate top-level keys
        assert 'architecture' in body
        arch = body['architecture']

        required = ['overview', 'architectureStyle', 'components',
                     'dataFlowSteps', 'mermaidDiagram', 'confidence']
        for key in required:
            assert key in arch, f"Missing key: {key}"

        assert isinstance(arch['components'], list)
        assert isinstance(arch['dataFlowSteps'], list)
        assert 0 <= arch['confidence'] <= 1
        assert arch['mermaidDiagram'].startswith('flowchart')

    def test_fallback_on_llm_failure(self, dynamodb_tables):
        _seed_repo(dynamodb_tables['repos'])

        with patch.dict('os.environ', {
            'REPOSITORIES_TABLE': 'BloomWay-Repositories',
            'CACHE_TABLE': 'BloomWay-Cache',
        }):
            import importlib
            import architecture as mod
            importlib.reload(mod)
            mod.repos_table = dynamodb_tables['repos']
            mod.cache_table = dynamodb_tables['cache']
            mod.bedrock_client = MagicMock()
            mod.bedrock_client.invoke_claude.side_effect = Exception("LLM down")
            mod.bedrock_client.ARCHITECTURE_SYSTEM_PROMPT = ''
            mod.vector_store = MagicMock()
            mod.vector_store.search.return_value = []

            resp = mod.lambda_handler(self._make_event(), None)

        assert resp['statusCode'] == 200
        body = json.loads(resp['body'])
        arch = body['architecture']
        assert arch['confidence'] == 0.0
        assert 'architectureStyle' in arch


# =====================================================================
#  5. Explain endpoint JSON schema tests
# =====================================================================
class TestExplainJsonSchema:
    """Validate the explain_file handler returns the correct JSON schema."""

    def _make_event(self, repo_id='test-repo-123', path='src/main.py', level='intermediate'):
        return {
            'pathParameters': {'id': repo_id, 'path': path},
            'queryStringParameters': {'level': level}
        }

    def test_full_schema_returned(self, dynamodb_tables):
        _seed_repo(dynamodb_tables['repos'])

        mock_explanation = json.dumps({
            'purpose': 'Main entry point',
            'businessContext': 'Handles API routing',
            'executionFlow': ['Step 1', 'Step 2'],
            'keyFunctions': [{'name': 'main', 'description': 'Entry', 'line': 1}],
            'designPatterns': ['Singleton'],
            'dependencies': ['flask'],
            'complexity': {'score': 3, 'reasoning': 'Simple file'},
            'improvementSuggestions': ['Add logging'],
            'securityRisks': ['None'],
            'impactAssessment': 'Core routing file',
            'confidence': 0.9
        })

        mock_chunks = [
            {'file_path': 'src/main.py', 'content': 'def main(): pass',
             'metadata': {'start_line': 0}},
        ]
        mock_related = [
            {'file_path': 'src/utils.py', 'content': 'def helper(): pass',
             'score': 0.85},
        ]

        with patch.dict('os.environ', {
            'REPOSITORIES_TABLE': 'BloomWay-Repositories',
            'CACHE_TABLE': 'BloomWay-Cache',
        }):
            import importlib
            import explain_file as mod
            importlib.reload(mod)
            mod.repos_table = dynamodb_tables['repos']
            mod.cache_table = dynamodb_tables['cache']
            mod.bedrock_client = MagicMock()
            mod.bedrock_client.invoke_claude.return_value = mock_explanation
            mod.bedrock_client.generate_embedding.return_value = [0.0] * 1024
            mod.vector_store = MagicMock()
            mod.vector_store.get_file_chunks.return_value = mock_chunks
            mod.vector_store.search.return_value = mock_related

            resp = mod.lambda_handler(self._make_event(), None)

        assert resp['statusCode'] == 200
        body = json.loads(resp['body'])
        expl = body['explanation']

        required = ['purpose', 'businessContext', 'executionFlow',
                     'keyFunctions', 'designPatterns', 'dependencies',
                     'complexity', 'improvementSuggestions', 'securityRisks',
                     'impactAssessment', 'confidence']
        for key in required:
            assert key in expl, f"Missing key: {key}"

        assert isinstance(expl['complexity'], dict)
        assert 'score' in expl['complexity']
        assert 0 <= expl['confidence'] <= 1

    def test_missing_file_returns_404(self, dynamodb_tables):
        _seed_repo(dynamodb_tables['repos'])

        with patch.dict('os.environ', {
            'REPOSITORIES_TABLE': 'BloomWay-Repositories',
            'CACHE_TABLE': 'BloomWay-Cache',
        }):
            import importlib
            import explain_file as mod
            importlib.reload(mod)
            mod.repos_table = dynamodb_tables['repos']
            mod.cache_table = dynamodb_tables['cache']
            mod.vector_store = MagicMock()
            mod.vector_store.get_file_chunks.return_value = []

            resp = mod.lambda_handler(self._make_event(), None)

        assert resp['statusCode'] == 404


# =====================================================================
#  6. Caching logic tests
# =====================================================================
class TestCachingLogic:
    """Test explanation caching: store, retrieve, and TTL expiry."""

    def test_cache_miss_then_hit(self, dynamodb_tables):
        _seed_repo(dynamodb_tables['repos'])

        mock_explanation = json.dumps({
            'purpose': 'Cached purpose',
            'businessContext': '', 'executionFlow': [],
            'keyFunctions': [], 'designPatterns': [],
            'dependencies': [],
            'complexity': {'score': 2, 'reasoning': 'Simple'},
            'improvementSuggestions': [], 'securityRisks': [],
            'impactAssessment': '', 'confidence': 0.8
        })

        mock_chunks = [
            {'file_path': 'src/main.py', 'content': 'x = 1',
             'metadata': {'start_line': 0}},
        ]

        with patch.dict('os.environ', {
            'REPOSITORIES_TABLE': 'BloomWay-Repositories',
            'CACHE_TABLE': 'BloomWay-Cache',
        }):
            import importlib
            import explain_file as mod
            importlib.reload(mod)
            mod.repos_table = dynamodb_tables['repos']
            mod.cache_table = dynamodb_tables['cache']
            mod.bedrock_client = MagicMock()
            mod.bedrock_client.invoke_claude.return_value = mock_explanation
            mod.bedrock_client.generate_embedding.return_value = [0.0] * 1024
            mod.vector_store = MagicMock()
            mod.vector_store.get_file_chunks.return_value = mock_chunks
            mod.vector_store.search.return_value = []

            event = {
                'pathParameters': {'id': 'test-repo-123', 'path': 'src/main.py'},
                'queryStringParameters': {'level': 'intermediate'}
            }

            # First call → cache miss, calls LLM
            resp1 = mod.lambda_handler(event, None)
            assert resp1['statusCode'] == 200
            assert mod.bedrock_client.invoke_claude.call_count == 1

            # Second call → cache hit, LLM NOT called again
            resp2 = mod.lambda_handler(event, None)
            assert resp2['statusCode'] == 200
            assert mod.bedrock_client.invoke_claude.call_count == 1  # still 1

            # Both responses should have same explanation
            body1 = json.loads(resp1['body'])
            body2 = json.loads(resp2['body'])
            assert body1['explanation']['purpose'] == body2['explanation']['purpose']

    def test_expired_cache_calls_llm_again(self, dynamodb_tables):
        """Manually insert an expired cache entry and verify LLM is called."""
        _seed_repo(dynamodb_tables['repos'])

        # Insert expired cache entry
        expired_ttl = int((datetime.utcnow() - timedelta(hours=1)).timestamp())
        dynamodb_tables['cache'].put_item(Item={
            'repo_id': 'test-repo-123',
            'sort_key': 'src/main.py#intermediate',
            'file_path': 'src/main.py',
            'level': 'intermediate',
            'data': {'repo_id': 'test-repo-123', 'explanation': {'purpose': 'old'}},
            'ttl': expired_ttl,
            'created_at': '2026-03-02T12:00:00Z'
        })

        mock_explanation = json.dumps({
            'purpose': 'Fresh purpose',
            'businessContext': '', 'executionFlow': [],
            'keyFunctions': [], 'designPatterns': [],
            'dependencies': [],
            'complexity': {'score': 1, 'reasoning': 'Trivial'},
            'improvementSuggestions': [], 'securityRisks': [],
            'impactAssessment': '', 'confidence': 0.5
        })

        mock_chunks = [
            {'file_path': 'src/main.py', 'content': 'y = 2',
             'metadata': {'start_line': 0}},
        ]

        with patch.dict('os.environ', {
            'REPOSITORIES_TABLE': 'BloomWay-Repositories',
            'CACHE_TABLE': 'BloomWay-Cache',
        }):
            import importlib
            import explain_file as mod
            importlib.reload(mod)
            mod.repos_table = dynamodb_tables['repos']
            mod.cache_table = dynamodb_tables['cache']
            mod.bedrock_client = MagicMock()
            mod.bedrock_client.invoke_claude.return_value = mock_explanation
            mod.bedrock_client.generate_embedding.return_value = [0.0] * 1024
            mod.vector_store = MagicMock()
            mod.vector_store.get_file_chunks.return_value = mock_chunks
            mod.vector_store.search.return_value = []

            event = {
                'pathParameters': {'id': 'test-repo-123', 'path': 'src/main.py'},
                'queryStringParameters': {'level': 'intermediate'}
            }

            resp = mod.lambda_handler(event, None)
            assert resp['statusCode'] == 200
            # LLM should be called because cache was expired
            assert mod.bedrock_client.invoke_claude.call_count == 1
            body = json.loads(resp['body'])
            assert body['explanation']['purpose'] == 'Fresh purpose'
