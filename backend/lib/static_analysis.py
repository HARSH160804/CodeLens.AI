"""
Lightweight static analysis via regex.
Extracts structural metadata from source code without any LLM calls.
"""
import re
from typing import Dict, Any, List


# ── Import patterns ──────────────────────────────────────────────
_IMPORT_PATTERNS = [
    # Python: import X / from X import Y
    re.compile(r'^\s*import\s+([\w.]+)', re.MULTILINE),
    re.compile(r'^\s*from\s+([\w.]+)\s+import', re.MULTILINE),
    # JS/TS: import ... from 'X' / require('X')
    re.compile(r'''^\s*import\s+.*?from\s+['"](.+?)['"]''', re.MULTILINE),
    re.compile(r'''require\(\s*['"](.+?)['"]\s*\)'''),
    # Java/C#: import X.Y.Z;
    re.compile(r'^\s*import\s+([\w.]+);', re.MULTILINE),
]

# ── Function name patterns ───────────────────────────────────────
_FUNC_NAME_PATTERNS = [
    # Python: def name(
    re.compile(r'^\s*(?:async\s+)?def\s+(\w+)\s*\(', re.MULTILINE),
    # JS/TS: function name( / async function name(
    re.compile(r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(', re.MULTILINE),
    # JS/TS arrow: const name = (...) =>
    re.compile(r'^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(', re.MULTILINE),
]

# ── Class name patterns ─────────────────────────────────────────
_CLASS_NAME_PATTERNS = [
    re.compile(r'^\s*(?:export\s+)?class\s+(\w+)', re.MULTILINE),
]

# ── Async usage indicators ───────────────────────────────────────
_ASYNC_KEYWORDS = re.compile(
    r'\b(async|await|Promise|asyncio|aiohttp|Task\.Run|CompletableFuture)\b'
)

# ── Database usage keywords ──────────────────────────────────────
_DB_KEYWORDS = re.compile(
    r'\b('
    r'SELECT|INSERT|UPDATE|DELETE|CREATE\s+TABLE|ALTER\s+TABLE|DROP\s+TABLE|'
    r'mongoose|sequelize|prisma|knex|typeorm|sqlalchemy|'
    r'dynamodb|DynamoDB|put_item|get_item|query|scan|'
    r'mongodb|MongoClient|collection\.|'
    r'redis|Redis|'
    r'pg\.connect|mysql\.create|sqlite3|'
    r'cursor\.execute|session\.query|\.findOne|\.findMany|\.aggregate'
    r')\b',
    re.IGNORECASE,
)

# ── API call patterns ────────────────────────────────────────────
_API_PATTERNS = re.compile(
    r'\b('
    r'fetch\s*\(|axios\.|requests\.(get|post|put|patch|delete)|'
    r'http\.request|urllib\.request|urlopen|'
    r'HttpClient|WebClient|RestTemplate|'
    r'\.get\s*\(\s*[\'"]https?://|\.post\s*\(\s*[\'"]https?://|'
    r'api_gateway|invoke_endpoint|'
    r'@app\.(get|post|put|delete|patch|route)|'
    r'@router\.(get|post|put|delete|patch)|'
    r'app\.(get|post|put|delete|patch)\s*\('
    r')\b',
    re.IGNORECASE,
)


def _unique_matches(code: str, patterns: list) -> List[str]:
    """Return a deduplicated, order-preserved list of all matches."""
    seen = set()
    results = []
    for pat in patterns:
        for m in pat.finditer(code):
            val = m.group(1)
            if val not in seen:
                seen.add(val)
                results.append(val)
    return results


def _keyword_hits(code: str, pattern: re.Pattern) -> List[str]:
    """Return deduplicated keyword hits from a single pattern."""
    seen = set()
    results = []
    for m in pattern.finditer(code):
        val = m.group(0).strip()
        key = val.lower()
        if key not in seen:
            seen.add(key)
            results.append(val)
    return results


def analyze_file_metadata(code_content: str) -> Dict[str, Any]:
    """
    Extract structural metadata from source code using regex only.

    Args:
        code_content: Raw source code as a string.

    Returns:
        {
            "imports": [...],
            "function_names": [...],
            "class_names": [...],
            "async_usage": [...],
            "db_keywords": [...],
            "api_patterns": [...]
        }
    """
    return {
        'imports': _unique_matches(code_content, _IMPORT_PATTERNS),
        'function_names': _unique_matches(code_content, _FUNC_NAME_PATTERNS),
        'class_names': _unique_matches(code_content, _CLASS_NAME_PATTERNS),
        'async_usage': _keyword_hits(code_content, _ASYNC_KEYWORDS),
        'db_keywords': _keyword_hits(code_content, _DB_KEYWORDS),
        'api_patterns': _keyword_hits(code_content, _API_PATTERNS),
    }
