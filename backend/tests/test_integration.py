"""
Backend integration test — exercises the full pipeline end-to-end.

Flow:
    1. Ingest a small synthetic test repo
    2. Call metadata endpoint
    3. Call architecture endpoint
    4. Call explain endpoint for a file
    5. Call explain again (verify caching — LLM not called twice)
    6. Assert JSON validity on every response
    7. Validate complexity score consistency
    8. Validate confidence override logic

All AWS services (DynamoDB, Bedrock) are mocked.
No frontend testing.
"""
import json
import os
import sys
import shutil
import tempfile
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
#  Fixtures
# =====================================================================

@pytest.fixture
def aws_env(monkeypatch):
    """Sets dummy AWS env vars."""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('REPOSITORIES_TABLE', 'BloomWay-Repositories')
    monkeypatch.setenv('CACHE_TABLE', 'BloomWay-Cache')
    monkeypatch.setenv('EMBEDDINGS_TABLE', 'BloomWay-Embeddings')


@pytest.fixture
def mock_tables(aws_env):
    """Provision mock DynamoDB tables used across all handlers."""
    with mock_aws():
        ddb = boto3.resource('dynamodb', region_name='us-east-1')

        repos = ddb.create_table(
            TableName='BloomWay-Repositories',
            KeySchema=[{'AttributeName': 'repo_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'repo_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

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
            BillingMode='PAY_PER_REQUEST',
        )

        embeddings = ddb.create_table(
            TableName='BloomWay-Embeddings',
            KeySchema=[
                {'AttributeName': 'repo_id', 'KeyType': 'HASH'},
                {'AttributeName': 'chunk_id', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'repo_id', 'AttributeType': 'S'},
                {'AttributeName': 'chunk_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )

        yield {
            'repos': repos,
            'cache': cache,
            'embeddings': embeddings,
            'resource': ddb,
        }


@pytest.fixture
def test_repo():
    """Create a small temporary repository on disk."""
    repo_dir = tempfile.mkdtemp(prefix='bloomway_test_repo_')

    # ── app.py ──
    with open(os.path.join(repo_dir, 'app.py'), 'w') as f:
        f.write('''\
"""Main application entry point."""
import os
from flask import Flask, jsonify

app = Flask(__name__)

class AppConfig:
    DEBUG = True
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok"})

@app.route('/api/data')
async def get_data():
    """Fetch data from database."""
    try:
        result = await fetch_from_db()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def fetch_from_db():
    """Query database."""
    import boto3
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('data')
    return table.scan()

if __name__ == '__main__':
    app.run()
''')

    # ── utils.py ──
    with open(os.path.join(repo_dir, 'utils.py'), 'w') as f:
        f.write('''\
"""Utility helpers."""
import re
import json
from typing import List, Dict, Any

def sanitize_input(text: str) -> str:
    """Remove dangerous characters."""
    return re.sub(r'[<>]', '', text)

def parse_config(path: str) -> Dict[str, Any]:
    """Read JSON config file."""
    with open(path, 'r') as f:
        return json.load(f)

def batch_process(items: List[Any], chunk_size: int = 10) -> List[List[Any]]:
    """Split list into batches."""
    return [items[i:i+chunk_size] for i in range(0, len(items), chunk_size)]
''')

    # ── requirements.txt ──
    with open(os.path.join(repo_dir, 'requirements.txt'), 'w') as f:
        f.write('flask>=2.0\nboto3\npytest\nredis\n')

    yield repo_dir
    shutil.rmtree(repo_dir, ignore_errors=True)


def _make_mock_bedrock():
    """Create a mock bedrock client that returns valid JSON."""
    mock = MagicMock()

    # generate_embedding → 1024-dim vector
    mock.generate_embedding.return_value = [0.01] * 1024

    # invoke_claude → valid JSON depending on prompt content
    def _invoke_claude(prompt, **kwargs):
        if 'architecture' in prompt.lower() or 'architectureStyle' in prompt:
            return json.dumps({
                'overview': 'A Flask web application with DynamoDB backend.',
                'architectureStyle': 'Monolithic MVC',
                'components': [
                    {'name': 'API Layer', 'description': 'Flask routes', 'files': ['app.py'], 'role': 'API Layer'},
                    {'name': 'Utilities', 'description': 'Helper functions', 'files': ['utils.py'], 'role': 'Shared'},
                ],
                'dataFlowSteps': [
                    'Step 1: Client sends HTTP request',
                    'Step 2: Flask routes handle request',
                    'Step 3: DynamoDB queried for data',
                    'Step 4: Response returned to client',
                ],
                'mermaidDiagram': 'flowchart TD\n    A[Client] --> B[Flask API]\n    B --> C[(DynamoDB)]',
                'confidence': 0.88,
            })
        else:
            return json.dumps({
                'purpose': 'Main application entry point for Flask API.',
                'businessContext': 'Serves the REST API for the product.',
                'executionFlow': ['Import dependencies', 'Configure app', 'Define routes', 'Run server'],
                'keyFunctions': [
                    {'name': 'health_check', 'description': 'Returns 200 OK', 'line': 13},
                    {'name': 'get_data', 'description': 'Fetches data from DB', 'line': 18},
                ],
                'designPatterns': ['Factory Pattern', 'MVC'],
                'dependencies': ['flask', 'boto3'],
                'complexity': {'score': 4, 'reasoning': 'Moderate — async routes with error handling'},
                'improvementSuggestions': ['Add input validation', 'Add rate limiting'],
                'securityRisks': ['Hardcoded fallback SECRET_KEY'],
                'impactAssessment': 'Core routing — changes affect all API endpoints.',
                'confidence': 0.92,
            })

    mock.invoke_claude.side_effect = _invoke_claude
    mock.ARCHITECTURE_SYSTEM_PROMPT = 'You are a software architect.'
    return mock


def _make_mock_vector_store(file_chunks_map):
    """Create a mock vector store seeded with file chunks."""
    mock = MagicMock()

    def _get_file_chunks(repo_id, file_path):
        return file_chunks_map.get(file_path, [])

    def _search(repo_id, embedding, top_k=5):
        results = []
        for fpath, chunks in file_chunks_map.items():
            for c in chunks:
                results.append({
                    'file_path': fpath,
                    'content': c['content'],
                    'score': 0.85,
                    'metadata': c.get('metadata', {}),
                })
        return results[:top_k]

    def _store_embeddings(repo_id, chunks):
        return len(chunks)

    mock.get_file_chunks.side_effect = _get_file_chunks
    mock.search.side_effect = _search
    mock.store_embeddings.side_effect = _store_embeddings
    return mock


# =====================================================================
#  Integration test
# =====================================================================

class TestEndToEndFlow:
    """Full backend integration test — no frontend, no real AWS."""

    # ── Step 1: Ingest ────────────────────────────────────────────

    def _ingest_repo(self, test_repo, tables, mock_bedrock, mock_vs):
        """Ingest the test repo and return the repo_id."""
        import importlib
        import ingest_repo as mod
        importlib.reload(mod)

        mod.repos_table = tables['repos']
        mod.bedrock_client = mock_bedrock
        mod.vector_store = mock_vs

        # Patch _download_github_repo to just return test_repo path
        with patch.object(mod, '_download_github_repo', return_value=test_repo):
            event = {
                'headers': {'content-type': 'application/json'},
                'body': json.dumps({'source': 'https://github.com/test/repo'}),
            }
            resp = mod.lambda_handler(event, None)

        assert resp['statusCode'] == 200, f"Ingest failed: {resp['body']}"
        body = json.loads(resp['body'])
        assert 'repo_id' in body
        return body['repo_id']

    # ── Step 2: Metadata ──────────────────────────────────────────

    def _call_metadata(self, repo_id, tables):
        import importlib
        import get_repo_metadata as mod
        importlib.reload(mod)
        mod.repos_table = tables['repos']

        event = {'pathParameters': {'id': repo_id}}
        resp = mod.lambda_handler(event, None)
        assert resp['statusCode'] == 200
        return json.loads(resp['body'])

    # ── Step 3: Architecture ──────────────────────────────────────

    def _call_architecture(self, repo_id, tables, mock_bedrock, mock_vs):
        import importlib
        import architecture as mod
        importlib.reload(mod)
        mod.repos_table = tables['repos']
        mod.cache_table = tables['cache']
        mod.bedrock_client = mock_bedrock
        mod.vector_store = mock_vs

        event = {
            'pathParameters': {'id': repo_id},
            'queryStringParameters': {'level': 'intermediate'},
        }
        resp = mod.lambda_handler(event, None)
        assert resp['statusCode'] == 200
        return json.loads(resp['body'])

    # ── Step 4 & 5: Explain (first call + cached call) ────────────

    def _call_explain(self, repo_id, file_path, tables, mock_bedrock, mock_vs):
        import importlib
        import explain_file as mod
        importlib.reload(mod)
        mod.repos_table = tables['repos']
        mod.cache_table = tables['cache']
        mod.bedrock_client = mock_bedrock
        mod.vector_store = mock_vs

        event = {
            'pathParameters': {'id': repo_id, 'path': file_path},
            'queryStringParameters': {'level': 'intermediate'},
        }
        resp = mod.lambda_handler(event, None)
        assert resp['statusCode'] == 200
        return json.loads(resp['body']), mod

    # ── Main test ─────────────────────────────────────────────────

    def test_full_pipeline(self, mock_tables, test_repo):
        """End-to-end: ingest → metadata → architecture → explain → cache."""

        # Prepare mocks
        mock_bedrock = _make_mock_bedrock()

        # Read test repo files for chunk seeding
        app_content = open(os.path.join(test_repo, 'app.py')).read()
        utils_content = open(os.path.join(test_repo, 'utils.py')).read()
        file_chunks = {
            'app.py': [{'content': app_content, 'metadata': {'start_line': 0}}],
            'utils.py': [{'content': utils_content, 'metadata': {'start_line': 0}}],
        }
        mock_vs = _make_mock_vector_store(file_chunks)

        # ────────────────────────────────────────────────────────
        #  STEP 1: Ingest small test repo
        # ────────────────────────────────────────────────────────
        repo_id = self._ingest_repo(test_repo, mock_tables, mock_bedrock, mock_vs)
        print(f"\n✅ Step 1  Ingest complete — repo_id={repo_id}")

        # ────────────────────────────────────────────────────────
        #  STEP 2: Call metadata endpoint
        # ────────────────────────────────────────────────────────
        metadata = self._call_metadata(repo_id, mock_tables)
        print(f"✅ Step 2  Metadata: {json.dumps(metadata, indent=2, default=str)[:300]}")

        # Assert JSON validity
        assert isinstance(metadata, dict)
        for key in ['repoName', 'totalFiles', 'totalLines',
                     'languageBreakdown', 'primaryLanguage', 'techStack',
                     'indexedAt']:
            assert key in metadata, f"Missing metadata key: {key}"

        assert metadata['totalFiles'] >= 2          # app.py + utils.py
        assert metadata['totalLines'] > 0
        assert metadata['primaryLanguage'] != ''

        # ────────────────────────────────────────────────────────
        #  STEP 3: Call architecture endpoint
        # ────────────────────────────────────────────────────────
        arch_resp = self._call_architecture(repo_id, mock_tables, mock_bedrock, mock_vs)
        arch = arch_resp['architecture']
        print(f"✅ Step 3  Architecture style: {arch.get('architectureStyle')}")

        # Assert JSON schema
        for key in ['overview', 'architectureStyle', 'components',
                     'dataFlowSteps', 'mermaidDiagram', 'confidence']:
            assert key in arch, f"Missing architecture key: {key}"

        assert isinstance(arch['components'], list)
        assert len(arch['components']) >= 1
        assert isinstance(arch['dataFlowSteps'], list)
        assert 0 <= arch['confidence'] <= 1
        assert arch['mermaidDiagram'].startswith('flowchart')

        # ────────────────────────────────────────────────────────
        #  STEP 4: Call explain endpoint (first — computes)
        # ────────────────────────────────────────────────────────
        explain_body, explain_mod = self._call_explain(
            repo_id, 'app.py', mock_tables, mock_bedrock, mock_vs
        )
        expl = explain_body['explanation']
        print(f"✅ Step 4  Explain purpose: {expl.get('purpose', '')[:80]}")

        # Assert JSON schema
        for key in ['purpose', 'businessContext', 'executionFlow',
                     'keyFunctions', 'designPatterns', 'dependencies',
                     'complexity', 'improvementSuggestions', 'securityRisks',
                     'impactAssessment', 'confidence']:
            assert key in expl, f"Missing explain key: {key}"

        assert isinstance(expl['complexity'], dict)
        assert 'score' in expl['complexity']
        assert 'reasoning' in expl['complexity']

        llm_calls_after_first = explain_mod.bedrock_client.invoke_claude.call_count

        # ────────────────────────────────────────────────────────
        #  STEP 5: Call explain again — verify caching
        # ────────────────────────────────────────────────────────
        explain_body_2, explain_mod_2 = self._call_explain(
            repo_id, 'app.py', mock_tables, mock_bedrock, mock_vs
        )
        llm_calls_after_second = explain_mod_2.bedrock_client.invoke_claude.call_count
        print(f"✅ Step 5  Caching verified — LLM calls: {llm_calls_after_first} → {llm_calls_after_second}")

        # LLM should NOT be called again (cache hit)
        assert llm_calls_after_second == llm_calls_after_first, \
            f"LLM was called again! Expected {llm_calls_after_first}, got {llm_calls_after_second}"

        # Cached response should match
        assert explain_body_2['explanation']['purpose'] == expl['purpose']

        # ────────────────────────────────────────────────────────
        #  STEP 6: Assert JSON validity (already covered above)
        # ────────────────────────────────────────────────────────
        print("✅ Step 6  All JSON responses validated")

        # ────────────────────────────────────────────────────────
        #  STEP 7: Validate complexity score consistency
        # ────────────────────────────────────────────────────────
        from complexity_analyzer import compute_complexity

        direct_complexity = compute_complexity(app_content)
        api_complexity_score = expl['complexity']['score']

        # The deterministic score should be 1-10
        assert 1 <= direct_complexity['score'] <= 10
        assert 1 <= api_complexity_score <= 10

        # Metrics should be consistent
        assert direct_complexity['metrics']['total_lines'] > 0
        assert direct_complexity['metrics']['function_count'] >= 2  # health_check, get_data, fetch_from_db
        print(f"✅ Step 7  Complexity: direct={direct_complexity['score']}, "
              f"api={api_complexity_score}, "
              f"functions={direct_complexity['metrics']['function_count']}")

        # ────────────────────────────────────────────────────────
        #  STEP 8: Validate confidence override logic
        # ────────────────────────────────────────────────────────
        from explain_file import _compute_deterministic_confidence

        # High confidence: similarity > 0.8, chunks >= 2
        high = _compute_deterministic_confidence([0.9, 0.85], 2, 1000)
        assert high >= 0.9, f"Expected High >= 0.9, got {high}"

        # Medium confidence: similarity > 0.6
        med = _compute_deterministic_confidence([0.7], 1, 500)
        assert 0.65 <= med <= 0.8, f"Expected Medium 0.65-0.8, got {med}"

        # Low confidence: similarity <= 0.6
        low = _compute_deterministic_confidence([0.4], 1, 200)
        assert low <= 0.5, f"Expected Low <= 0.5, got {low}"

        # No context at all
        none_conf = _compute_deterministic_confidence([], 0, 100)
        assert none_conf == 0.3, f"Expected 0.3, got {none_conf}"

        # Verify the explain endpoint applied the override (not the LLM's 0.92)
        api_conf = expl['confidence']
        assert api_conf != 0.92, \
            f"Confidence was NOT overridden! Still LLM value 0.92. Got {api_conf}"
        assert 0 <= api_conf <= 1
        print(f"✅ Step 8  Confidence override: LLM=0.92, actual={api_conf}")

        print("\n🎉 All 8 integration steps passed!\n")
