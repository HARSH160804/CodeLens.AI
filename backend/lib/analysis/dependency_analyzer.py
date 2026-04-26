"""
Dependency Analyzer for Architecture Analysis

Analyzes package dependencies, detects circular dependencies, identifies vulnerabilities.
"""

import json
import logging
from typing import List, Dict, Any, Set, Tuple

from bedrock_client import BedrockClient
from models.architecture_models import (
    DependencyAnalysis,
    DependencyTree,
    DependencyNode,
    CircularDependency,
    OutdatedPackage,
    DependencyVulnerability,
    LicenseIssue,
    Vulnerability
)

logger = logging.getLogger(__name__)


class DependencyAnalyzer:
    """Analyzes package dependencies and relationships."""
    
    def __init__(self, bedrock_client: BedrockClient = None):
        """
        Initialize dependency analyzer.
        
        Args:
            bedrock_client: Optional Bedrock client for AI analysis
        """
        self.bedrock_client = bedrock_client or BedrockClient()
    
    def analyze_dependencies(
        self,
        context: Dict[str, Any]
    ) -> DependencyAnalysis:
        """
        Analyze package dependencies and relationships.
        
        Args:
            context: Analysis context
            
        Returns:
            Complete dependency analysis with tree, cycles, vulnerabilities
        """
        try:
            # Build dependency tree
            dependency_tree = self._build_dependency_tree(context)
            
            # Detect circular dependencies
            circular_dependencies = self._detect_circular_dependencies(context)
            
            # Check for outdated packages
            outdated_packages = self._check_outdated_packages(context)
            
            # Scan for vulnerabilities
            vulnerabilities = self._scan_vulnerabilities(context)
            
            # Analyze license compatibility
            license_issues = self._analyze_licenses(context)
            
            analysis = DependencyAnalysis(
                dependency_tree=dependency_tree,
                circular_dependencies=circular_dependencies,
                outdated_packages=outdated_packages,
                vulnerabilities=vulnerabilities,
                license_issues=license_issues
            )
            
            logger.info(f"Analyzed dependencies: {dependency_tree.total_dependencies} total, "
                       f"{len(circular_dependencies)} circular, {len(vulnerabilities)} vulnerabilities")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing dependencies: {str(e)}")
            return self._default_analysis()
    
    def _build_dependency_tree(self, context: Dict[str, Any]) -> DependencyTree:
        """
        Construct hierarchical tree.
        
        Args:
            context: Analysis context
            
        Returns:
            Dependency tree with depth levels
        """
        repo_metadata = context.get('repo_metadata', {})
        repo_name = repo_metadata.get('name', 'root')
        
        # Create root node
        root = DependencyNode(
            package_name=repo_name,
            version='1.0.0',
            license='MIT',
            depth=0,
            children=[],
            security_status='secure'
        )
        
        # Parse dependencies from file summaries
        file_summaries = context.get('file_summaries', [])
        dependencies = self._extract_dependencies(file_summaries)
        
        # Build tree structure
        max_depth = 0
        for dep_name, dep_info in dependencies.items():
            child = DependencyNode(
                package_name=dep_name,
                version=dep_info.get('version', 'unknown'),
                license=dep_info.get('license'),
                depth=1,
                children=[],
                security_status=dep_info.get('security_status', 'unknown')
            )
            root.children.append(child)
            max_depth = max(max_depth, 1)
        
        tree = DependencyTree(
            root=root,
            total_dependencies=len(dependencies),
            max_depth=max_depth
        )
        
        return tree
    
    def _extract_dependencies(self, file_summaries: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Extract dependencies from package files."""
        dependencies = {}
        
        for f in file_summaries:
            file_path = f.get('file_path', '').lower()
            content = f.get('content', '')
            
            # Python requirements.txt
            if file_path.endswith('requirements.txt'):
                deps = self._parse_requirements_deps(content)
                dependencies.update(deps)
            
            # Node package.json
            elif file_path.endswith('package.json'):
                deps = self._parse_package_json_deps(content)
                dependencies.update(deps)
        
        return dependencies
    
    def _parse_requirements_deps(self, content: str) -> Dict[str, Dict[str, Any]]:
        """Parse Python requirements.txt."""
        dependencies = {}
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse package==version
            if '==' in line:
                parts = line.split('==')
                if len(parts) == 2:
                    package_name = parts[0].strip()
                    version = parts[1].strip()
                    dependencies[package_name] = {
                        'version': version,
                        'license': None,
                        'security_status': 'unknown'
                    }
        
        return dependencies
    
    def _parse_package_json_deps(self, content: str) -> Dict[str, Dict[str, Any]]:
        """Parse Node package.json."""
        dependencies = {}
        
        try:
            data = json.loads(content)
            
            for dep_type in ['dependencies', 'devDependencies']:
                deps = data.get(dep_type, {})
                for package_name, version in deps.items():
                    version_clean = version.lstrip('^~>=<')
                    dependencies[package_name] = {
                        'version': version_clean,
                        'license': None,
                        'security_status': 'unknown'
                    }
        
        except json.JSONDecodeError:
            pass
        
        return dependencies
    
    def _detect_circular_dependencies(self, context: Dict[str, Any]) -> List[CircularDependency]:
        """
        Find dependency cycles.
        
        Args:
            context: Analysis context
            
        Returns:
            List of circular dependencies
        """
        circular_deps = []
        
        # Build dependency graph from imports
        file_summaries = context.get('file_summaries', [])
        dependency_graph = self._build_dependency_graph(file_summaries)
        
        # Detect cycles using DFS
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in dependency_graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle_path = path[cycle_start:] + [neighbor]
                    
                    circular_dep = CircularDependency(
                        cycle_path=cycle_path,
                        severity='high' if len(cycle_path) <= 3 else 'medium',
                        description=f"Circular dependency detected: {' -> '.join(cycle_path)}"
                    )
                    circular_deps.append(circular_dep)
            
            rec_stack.remove(node)
        
        # Run DFS from each node
        for node in dependency_graph.keys():
            if node not in visited:
                dfs(node, [])
        
        return circular_deps[:10]  # Limit to 10
    
    def _build_dependency_graph(self, file_summaries: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Build graph from file imports."""
        graph = {}
        
        for f in file_summaries:
            file_path = f.get('file_path', '')
            content = f.get('content', '')
            
            # Extract imports (simplified)
            imports = self._extract_imports(content, file_path)
            
            if imports:
                graph[file_path] = imports
        
        return graph
    
    def _extract_imports(self, content: str, file_path: str) -> List[str]:
        """Extract import statements from file content."""
        imports = []
        
        # Python imports
        if file_path.endswith('.py'):
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    # Extract module name
                    parts = line.split()
                    if len(parts) >= 2:
                        module = parts[1].split('.')[0]
                        imports.append(module)
        
        # JavaScript/TypeScript imports
        elif file_path.endswith(('.js', '.ts', '.jsx', '.tsx')):
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('import '):
                    # Extract module name from: import X from 'module'
                    if 'from' in line:
                        parts = line.split('from')
                        if len(parts) >= 2:
                            module = parts[1].strip().strip("';\"")
                            imports.append(module)
        
        return imports
    
    def _check_outdated_packages(self, context: Dict[str, Any]) -> List[OutdatedPackage]:
        """
        Compare with latest versions.
        
        Args:
            context: Analysis context
            
        Returns:
            List of outdated packages
        """
        # This would query package registries in production
        # For now, return empty list
        return []
    
    def _scan_vulnerabilities(self, context: Dict[str, Any]) -> List[DependencyVulnerability]:
        """
        Check for known CVEs.
        
        Args:
            context: Analysis context
            
        Returns:
            List of vulnerabilities
        """
        # This would query vulnerability databases in production
        # For now, return empty list
        return []
    
    def _analyze_licenses(self, context: Dict[str, Any]) -> List[LicenseIssue]:
        """
        Check license compatibility.
        
        Args:
            context: Analysis context
            
        Returns:
            List of license issues
        """
        # This would check license compatibility in production
        # For now, return empty list
        return []
    
    def _default_analysis(self) -> DependencyAnalysis:
        """Return default analysis when calculation fails."""
        root = DependencyNode(
            package_name='root',
            version='1.0.0',
            license=None,
            depth=0,
            children=[],
            security_status='unknown'
        )
        
        tree = DependencyTree(
            root=root,
            total_dependencies=0,
            max_depth=0
        )
        
        return DependencyAnalysis(
            dependency_tree=tree,
            circular_dependencies=[],
            outdated_packages=[],
            vulnerabilities=[],
            license_issues=[]
        )
