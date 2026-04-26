"""Code parsing and chunking utilities."""
import json
import os
import re
import tempfile
import shutil
import zipfile
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
import subprocess


class RepositoryProcessor:
    """Process and analyze source code repositories."""
    
    SUPPORTED_EXTENSIONS = {'.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rb', '.php', '.cpp', '.c', '.h', '.cs', '.rs'}
    EXCLUDED_DIRS = {'node_modules', '.git', '__pycache__', 'venv', 'env', 'dist', 'build', '.next', 'target', 'vendor'}
    MAX_FILE_SIZE_MB = 5
    MAX_CHUNK_TOKENS = 1000
    CHUNK_OVERLAP_TOKENS = 100
    
    def __init__(self, progress_callback: Optional[Callable[[str, int], None]] = None):
        """
        Initialize repository processor.
        
        Args:
            progress_callback: Optional callback for progress updates (message, percentage)
        """
        self.progress_callback = progress_callback
    
    def _report_progress(self, message: str, percentage: int = 0) -> None:
        """Report progress if callback is set."""
        if self.progress_callback:
            self.progress_callback(message, percentage)
    
    def clone_repository(self, url: str, token: Optional[str] = None) -> str:
        """
        Clone a GitHub repository to temporary storage.
        
        Args:
            url: GitHub repository URL
            token: Optional GitHub OAuth token
            
        Returns:
            Path to cloned repository
            
        Raises:
            RuntimeError: If clone fails
        """
        self._report_progress("Cloning repository...", 10)
        
        temp_dir = tempfile.mkdtemp(prefix='bloomway_repo_')
        
        try:
            clone_url = url
            if token and 'github.com' in url:
                clone_url = url.replace('https://', f'https://{token}@')
            
            result = subprocess.run(
                ['git', 'clone', '--depth', '1', clone_url, temp_dir],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Git clone failed: {result.stderr}")
            
            self._report_progress("Repository cloned successfully", 20)
            return temp_dir
            
        except subprocess.TimeoutExpired:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError("Repository clone timed out after 5 minutes")
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError(f"Failed to clone repository: {str(e)}")
    
    def extract_zip(self, file_path: str) -> str:
        """
        Extract uploaded ZIP archive.
        
        Args:
            file_path: Path to ZIP file
            
        Returns:
            Path to extracted directory
            
        Raises:
            RuntimeError: If extraction fails
        """
        self._report_progress("Extracting archive...", 10)
        
        temp_dir = tempfile.mkdtemp(prefix='bloomway_extract_')
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            self._report_progress("Archive extracted successfully", 20)
            return temp_dir
            
        except zipfile.BadZipFile:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError("Invalid ZIP file")
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError(f"Failed to extract archive: {str(e)}")
    
    def discover_files(self, repo_path: str) -> List[Dict[str, Any]]:
        """
        Discover source code files in repository.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            List of file metadata dicts
        """
        self._report_progress("Discovering files...", 30)
        
        files = []
        repo_path_obj = Path(repo_path)
        
        for file_path in repo_path_obj.rglob('*'):
            if not file_path.is_file():
                continue
            
            # Skip excluded directories
            if any(excluded in file_path.parts for excluded in self.EXCLUDED_DIRS):
                continue
            
            # Check extension
            if file_path.suffix not in self.SUPPORTED_EXTENSIONS:
                continue
            
            # Check file size
            try:
                size_mb = file_path.stat().st_size / (1024 * 1024)
                if size_mb > self.MAX_FILE_SIZE_MB:
                    continue
            except OSError:
                continue
            
            # Check if binary
            if self._is_binary(file_path):
                continue
            
            relative_path = str(file_path.relative_to(repo_path))
            
            files.append({
                'path': str(file_path),
                'relative_path': relative_path,
                'extension': file_path.suffix,
                'size_bytes': file_path.stat().st_size,
                'name': file_path.name
            })
        
        self._report_progress(f"Discovered {len(files)} files", 40)
        return files
    
    def _is_binary(self, file_path: Path) -> bool:
        """Check if file is binary."""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\x00' in chunk
        except Exception:
            return True
    
    def extract_imports(self, file_path: str) -> List[str]:
        """
        Extract import statements using regex.
        
        Args:
            file_path: Path to source file
            
        Returns:
            List of imported modules/packages
        """
        imports = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            ext = Path(file_path).suffix
            
            if ext == '.py':
                # Python imports
                patterns = [
                    r'^\s*import\s+([\w.]+)',
                    r'^\s*from\s+([\w.]+)\s+import',
                ]
            elif ext in {'.js', '.ts', '.jsx', '.tsx'}:
                # JavaScript/TypeScript imports
                patterns = [
                    r'^\s*import\s+.*?from\s+[\'"]([^\'"]+)[\'"]',
                    r'^\s*require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
                ]
            elif ext == '.java':
                # Java imports
                patterns = [r'^\s*import\s+([\w.]+);']
            elif ext == '.go':
                # Go imports
                patterns = [r'^\s*import\s+"([^"]+)"']
            else:
                return imports
            
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.MULTILINE)
                imports.extend([m.group(1) for m in matches])
        
        except Exception:
            pass
        
        return list(set(imports))
    
    def identify_entry_points(self, files: List[Dict[str, Any]]) -> List[str]:
        """
        Identify entry point files.
        
        Args:
            files: List of file metadata dicts
            
        Returns:
            List of entry point file paths
        """
        entry_points = []
        
        entry_patterns = {
            'main.py', 'app.py', '__main__.py', 'manage.py',
            'index.js', 'index.ts', 'main.js', 'main.ts', 'app.js', 'app.ts',
            'server.js', 'server.ts',
            'Main.java', 'Application.java',
            'main.go',
        }
        
        for file_info in files:
            name = file_info['name']
            
            if name in entry_patterns:
                entry_points.append(file_info['relative_path'])
                continue
            
            # Check for main function
            try:
                with open(file_info['path'], 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(5000)  # Check first 5000 chars
                    
                    if 'if __name__ == "__main__"' in content:
                        entry_points.append(file_info['relative_path'])
                    elif 'func main()' in content:
                        entry_points.append(file_info['relative_path'])
                    elif 'public static void main' in content:
                        entry_points.append(file_info['relative_path'])
            except Exception:
                pass
        
        return entry_points
    
    def estimate_complexity(self, file_path: str) -> Dict[str, Any]:
        """
        Estimate file complexity metrics.
        
        Args:
            file_path: Path to source file
            
        Returns:
            Dict with complexity metrics
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            code_lines = 0
            comment_lines = 0
            blank_lines = 0
            function_count = 0
            class_count = 0
            
            ext = Path(file_path).suffix
            
            for line in lines:
                stripped = line.strip()
                
                if not stripped:
                    blank_lines += 1
                elif self._is_comment_line(stripped, ext):
                    comment_lines += 1
                else:
                    code_lines += 1
                    
                    # Count functions and classes
                    if ext == '.py':
                        if stripped.startswith('def '):
                            function_count += 1
                        elif stripped.startswith('class '):
                            class_count += 1
                    elif ext in {'.js', '.ts', '.jsx', '.tsx'}:
                        if re.match(r'^\s*(function|const|let|var)\s+\w+\s*=?\s*(\(|function)', stripped):
                            function_count += 1
                        elif stripped.startswith('class '):
                            class_count += 1
                    elif ext == '.java':
                        if re.match(r'^\s*(public|private|protected)?\s*(static)?\s*\w+\s+\w+\s*\(', stripped):
                            function_count += 1
                        elif re.match(r'^\s*(public|private|protected)?\s*class\s+', stripped):
                            class_count += 1
            
            comment_ratio = comment_lines / total_lines if total_lines > 0 else 0
            
            return {
                'total_lines': total_lines,
                'code_lines': code_lines,
                'comment_lines': comment_lines,
                'blank_lines': blank_lines,
                'comment_ratio': round(comment_ratio, 2),
                'function_count': function_count,
                'class_count': class_count,
                'estimated_complexity': 'low' if code_lines < 100 else 'medium' if code_lines < 500 else 'high'
            }
            
        except Exception:
            return {
                'total_lines': 0,
                'code_lines': 0,
                'comment_lines': 0,
                'blank_lines': 0,
                'comment_ratio': 0,
                'function_count': 0,
                'class_count': 0,
                'estimated_complexity': 'unknown'
            }
    
    def _is_comment_line(self, line: str, ext: str) -> bool:
        """Check if line is a comment."""
        if ext == '.py':
            return line.startswith('#')
        elif ext in {'.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.c', '.cpp', '.cs', '.rs'}:
            return line.startswith('//') or line.startswith('/*') or line.startswith('*')
        return False
    
    def semantic_chunking(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """
        Split code into semantic chunks.
        
        Args:
            file_path: Path to source file
            content: File content
            
        Returns:
            List of chunk dicts
        """
        chunks = []
        lines = content.split('\n')
        ext = Path(file_path).suffix
        
        # Find function/class boundaries
        boundaries = self._find_boundaries(lines, ext)
        
        if not boundaries:
            # No boundaries found, chunk by line count
            return self._chunk_by_lines(content, file_path)
        
        # Create chunks from boundaries
        for i, (start, end, chunk_type) in enumerate(boundaries):
            chunk_content = '\n'.join(lines[start:end])
            chunk_tokens = len(chunk_content) // 4  # Rough estimate
            
            if chunk_tokens > self.MAX_CHUNK_TOKENS:
                # Split large chunks
                sub_chunks = self._split_large_chunk(chunk_content, start, file_path)
                chunks.extend(sub_chunks)
            else:
                chunks.append({
                    'content': chunk_content,
                    'start_line': start + 1,
                    'end_line': end,
                    'type': chunk_type,
                    'index': len(chunks)
                })
        
        # Add overlap between chunks
        chunks = self._add_overlap(chunks, lines)
        
        return chunks
    
    def _find_boundaries(self, lines: List[str], ext: str) -> List[tuple]:
        """Find function/class boundaries."""
        boundaries = []
        current_start = None
        current_type = None
        indent_stack = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            if not stripped or self._is_comment_line(stripped, ext):
                continue
            
            indent = len(line) - len(line.lstrip())
            
            # Detect function/class start
            is_function = False
            is_class = False
            
            if ext == '.py':
                is_function = stripped.startswith('def ')
                is_class = stripped.startswith('class ')
            elif ext in {'.js', '.ts', '.jsx', '.tsx'}:
                is_function = bool(re.match(r'^(function|const|let|var)\s+\w+', stripped))
                is_class = stripped.startswith('class ')
            elif ext == '.java':
                is_function = bool(re.match(r'^(public|private|protected)?\s*(static)?\s*\w+\s+\w+\s*\(', stripped))
                is_class = bool(re.match(r'^(public|private|protected)?\s*class\s+', stripped))
            
            if is_function or is_class:
                if current_start is not None:
                    boundaries.append((current_start, i, current_type))
                current_start = i
                current_type = 'class' if is_class else 'function'
                indent_stack = [indent]
            elif current_start is not None:
                # Check if we've exited the current block
                if indent_stack and indent <= indent_stack[0]:
                    boundaries.append((current_start, i, current_type))
                    current_start = None
                    current_type = None
                    indent_stack = []
        
        # Add final boundary
        if current_start is not None:
            boundaries.append((current_start, len(lines), current_type))
        
        return boundaries
    
    def _chunk_by_lines(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Chunk by line count when no boundaries found."""
        lines = content.split('\n')
        chunk_size = 50  # lines per chunk
        chunks = []
        
        for i in range(0, len(lines), chunk_size):
            chunk_lines = lines[i:i + chunk_size]
            chunks.append({
                'content': '\n'.join(chunk_lines),
                'start_line': i + 1,
                'end_line': min(i + chunk_size, len(lines)),
                'type': 'block',
                'index': len(chunks)
            })
        
        return chunks
    
    def _split_large_chunk(self, content: str, start_line: int, file_path: str) -> List[Dict[str, Any]]:
        """Split large chunk into smaller pieces."""
        lines = content.split('\n')
        chunk_size = 30
        chunks = []
        
        for i in range(0, len(lines), chunk_size):
            chunk_lines = lines[i:i + chunk_size]
            chunks.append({
                'content': '\n'.join(chunk_lines),
                'start_line': start_line + i + 1,
                'end_line': start_line + min(i + chunk_size, len(lines)),
                'type': 'sub-block',
                'index': len(chunks)
            })
        
        return chunks
    
    def _add_overlap(self, chunks: List[Dict[str, Any]], lines: List[str]) -> List[Dict[str, Any]]:
        """Add overlap between chunks."""
        overlap_lines = 5
        
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]
            
            # Add last few lines of current chunk to next chunk
            overlap_start = max(0, current_chunk['end_line'] - overlap_lines - 1)
            overlap_end = current_chunk['end_line']
            overlap_content = '\n'.join(lines[overlap_start:overlap_end])
            
            if overlap_content:
                next_chunk['content'] = overlap_content + '\n' + next_chunk['content']
        
        return chunks
    
    def create_chunk_metadata(self, chunk: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """
        Create metadata for a chunk.
        
        Args:
            chunk: Chunk dict
            file_path: Path to source file
            
        Returns:
            Metadata dict
        """
        return {
            'file_path': file_path,
            'start_line': chunk['start_line'],
            'end_line': chunk['end_line'],
            'type': chunk['type'],
            'index': chunk['index'],
            'language': Path(file_path).suffix[1:],
            'size': len(chunk['content'])
        }
    
    # ── Known-keyword lookup tables for manifest scanning ────────────
    _JS_FRAMEWORKS = {
        'react': 'React', 'next': 'Next.js', 'vue': 'Vue.js', 'nuxt': 'Nuxt.js',
        'angular': 'Angular', 'svelte': 'Svelte', 'express': 'Express',
        'fastify': 'Fastify', 'nestjs': 'NestJS', 'koa': 'Koa',
        'gatsby': 'Gatsby', 'remix': 'Remix', 'electron': 'Electron',
        'tailwindcss': 'TailwindCSS', 'vite': 'Vite',
    }
    _PY_FRAMEWORKS = {
        'django': 'Django', 'flask': 'Flask', 'fastapi': 'FastAPI',
        'tornado': 'Tornado', 'celery': 'Celery', 'scrapy': 'Scrapy',
        'pytest': 'pytest', 'pandas': 'Pandas', 'numpy': 'NumPy',
        'boto3': 'AWS SDK (boto3)', 'tensorflow': 'TensorFlow',
        'torch': 'PyTorch', 'langchain': 'LangChain',
        'streamlit': 'Streamlit', 'sqlalchemy': 'SQLAlchemy',
    }
    _DB_KEYWORDS = {
        'mongoose': 'MongoDB', 'mongodb': 'MongoDB', 'pymongo': 'MongoDB',
        'pg': 'PostgreSQL', 'psycopg2': 'PostgreSQL', 'postgres': 'PostgreSQL',
        'mysql': 'MySQL', 'mysql2': 'MySQL',
        'redis': 'Redis', 'ioredis': 'Redis',
        'sqlite3': 'SQLite', 'sqlite': 'SQLite',
        'dynamodb': 'DynamoDB', 'boto3': 'DynamoDB',
        'sequelize': 'SQL (Sequelize)', 'prisma': 'Prisma ORM',
        'typeorm': 'TypeORM', 'knex': 'Knex.js',
        'elasticsearch': 'Elasticsearch', 'cassandra': 'Cassandra',
    }

    def detect_tech_stack(self, files: List[Dict[str, Any]], repo_path: str = None) -> Dict[str, Any]:
        """
        Detect technology stack from files.
        
        Args:
            files: List of file metadata dicts
            repo_path: Path to repository root (used to read manifest files)
            
        Returns:
            Dict with detected technologies
        """
        self._report_progress("Detecting tech stack...", 60)
        
        languages = set()
        frameworks = set()
        libraries = set()
        databases = set()
        
        # Detect languages from file extensions
        for file_info in files:
            ext = file_info['extension']
            if ext == '.py':
                languages.add('Python')
            elif ext in {'.js', '.jsx'}:
                languages.add('JavaScript')
            elif ext in {'.ts', '.tsx'}:
                languages.add('TypeScript')
            elif ext == '.java':
                languages.add('Java')
            elif ext == '.go':
                languages.add('Go')
            elif ext == '.rb':
                languages.add('Ruby')
            elif ext == '.php':
                languages.add('PHP')
        
        # Check for config files in source files list
        for file_info in files:
            file_name = file_info['name']
            
            # Framework-specific config files
            if file_name in {'next.config.js', 'next.config.ts', 'next.config.mjs'}:
                frameworks.add('Next.js')
            elif file_name in {'nuxt.config.js', 'nuxt.config.ts'}:
                frameworks.add('Nuxt.js')
            elif file_name == 'angular.json':
                frameworks.add('Angular')
            elif file_name == 'vue.config.js':
                frameworks.add('Vue.js')
            
            # Extract imports for library/framework detection
            imports = self.extract_imports(file_info['path'])
            for imp in imports:
                imp_lower = imp.lower()
                if 'react' in imp_lower:
                    libraries.add('React')
                if 'django' in imp_lower:
                    frameworks.add('Django')
                if 'flask' in imp_lower:
                    frameworks.add('Flask')
                if 'express' in imp_lower:
                    frameworks.add('Express')
                if 'spring' in imp_lower:
                    frameworks.add('Spring')
                if 'fastapi' in imp_lower:
                    frameworks.add('FastAPI')
        
        # ── Scan manifest files directly from disk ──────────────────
        if repo_path:
            self._scan_manifests(repo_path, languages, frameworks, databases)
        
        return {
            'languages': sorted(list(languages)),
            'frameworks': sorted(list(frameworks)),
            'libraries': sorted(list(libraries)),
            'databases': sorted(list(databases))
        }
    
    def _scan_manifests(
        self,
        repo_path: str,
        languages: set,
        frameworks: set,
        databases: set
    ) -> None:
        """
        Walk repo_path and read manifest files to detect frameworks & databases.
        Mutates the provided sets in-place.
        """
        for dirpath, _dirs, filenames in os.walk(repo_path):
            # Skip excluded directories
            if any(excl in Path(dirpath).parts for excl in self.EXCLUDED_DIRS):
                continue
            
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                try:
                    if fname == 'package.json':
                        languages.add('JavaScript')
                        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                            pkg = json.loads(f.read())
                        all_deps = {}
                        all_deps.update(pkg.get('dependencies', {}))
                        all_deps.update(pkg.get('devDependencies', {}))
                        for dep_name in all_deps:
                            dep_lower = dep_name.lower().replace('@', '').split('/')[0]
                            if dep_lower in self._JS_FRAMEWORKS:
                                frameworks.add(self._JS_FRAMEWORKS[dep_lower])
                            if dep_lower in self._DB_KEYWORDS:
                                databases.add(self._DB_KEYWORDS[dep_lower])
                        if 'typescript' in all_deps or 'ts-node' in all_deps:
                            languages.add('TypeScript')
                    
                    elif fname == 'requirements.txt':
                        languages.add('Python')
                        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                            for line in f:
                                dep = re.split(r'[>=<!\[\]]', line.strip().lower())[0].strip()
                                if dep in self._PY_FRAMEWORKS:
                                    frameworks.add(self._PY_FRAMEWORKS[dep])
                                if dep in self._DB_KEYWORDS:
                                    databases.add(self._DB_KEYWORDS[dep])
                    
                    elif fname == 'Gemfile':
                        languages.add('Ruby')
                    
                    elif fname == 'go.mod':
                        languages.add('Go')
                        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read().lower()
                        if 'gin-gonic' in content:
                            frameworks.add('Gin')
                        if 'echo' in content:
                            frameworks.add('Echo')
                        if 'fiber' in content:
                            frameworks.add('Fiber')
                    
                    elif fname == 'pom.xml':
                        languages.add('Java')
                        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read().lower()
                        if 'spring-boot' in content:
                            frameworks.add('Spring Boot')
                        if 'spring-web' in content or 'spring-mvc' in content:
                            frameworks.add('Spring MVC')
                
                except Exception:
                    continue
    
    def build_dependency_graph(self, files: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Build file dependency graph.
        
        Args:
            files: List of file metadata dicts
            
        Returns:
            Dict mapping file paths to their dependencies
        """
        self._report_progress("Building dependency graph...", 80)
        
        graph = {}
        
        for file_info in files:
            file_path = file_info['relative_path']
            imports = self.extract_imports(file_info['path'])
            
            dependencies = []
            for imp in imports:
                # Try to match import to actual files
                for other_file in files:
                    other_path = other_file['relative_path']
                    if imp in other_path or other_path.replace('/', '.').replace('\\', '.') in imp:
                        dependencies.append(other_path)
            
            graph[file_path] = dependencies
        
        self._report_progress("Dependency graph built", 90)
        return graph
