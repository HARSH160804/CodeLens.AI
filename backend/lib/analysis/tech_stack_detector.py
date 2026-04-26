"""
Tech Stack Detector for Architecture Analysis

Identifies technologies, versions, licenses, and security status.
Integrates with TechnologyClassifier for intelligent category detection.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional

from models.architecture_models import Technology, Vulnerability

# Import TechnologyClassifier for intelligent classification
try:
    from services.technology_classifier import TechnologyClassifier
    CLASSIFIER_AVAILABLE = True
except ImportError:
    CLASSIFIER_AVAILABLE = False
    logging.warning("TechnologyClassifier not available, using fallback classification")

logger = logging.getLogger(__name__)


class TechStackDetector:
    """Identifies technologies, versions, licenses, and security status."""
    
    def __init__(self, bedrock_client=None, redis_client=None):
        """
        Initialize tech stack detector.
        
        Args:
            bedrock_client: Optional Bedrock client for LLM classification
            redis_client: Optional Redis client for caching
        """
        # Initialize TechnologyClassifier if available
        if CLASSIFIER_AVAILABLE:
            self.classifier = TechnologyClassifier(
                bedrock_client=bedrock_client,
                redis_client=redis_client
            )
            logger.info("TechnologyClassifier initialized for intelligent category detection")
        else:
            self.classifier = None
            logger.warning("TechnologyClassifier not available, using static category mapping")
    
    def detect_tech_stack(
        self,
        context: Dict[str, Any]
    ) -> List[Technology]:
        """
        Detect all technologies used in codebase.
        
        Args:
            context: Analysis context
            
        Returns:
            List of detected technologies with metadata
        """
        try:
            technologies = []
            
            # Parse package files
            package_techs = self._parse_package_files(context)
            technologies.extend(package_techs)
            
            # Detect from file extensions
            extension_techs = self._detect_from_extensions(context)
            technologies.extend(extension_techs)
            
            # Detect frameworks from file patterns
            framework_techs = self._detect_frameworks(context)
            technologies.extend(framework_techs)
            
            # Deduplicate by name
            unique_techs = self._deduplicate_technologies(technologies)
            
            logger.info(f"Detected {len(unique_techs)} technologies")
            return unique_techs
            
        except Exception as e:
            logger.error(f"Error detecting tech stack: {str(e)}")
            return []
    
    def _parse_package_files(self, context: Dict[str, Any]) -> List[Technology]:
        """
        Extract from package.json, requirements.txt, etc.
        
        Args:
            context: Analysis context
            
        Returns:
            List of technologies from package files
        """
        technologies = []
        file_summaries = context.get('file_summaries', [])
        
        for f in file_summaries:
            file_path = f.get('file_path', '').lower()
            content = f.get('content', '')
            
            # Python requirements.txt
            if file_path.endswith('requirements.txt'):
                techs = self._parse_requirements_txt(content)
                technologies.extend(techs)
            
            # Python Pipfile
            elif file_path.endswith('pipfile'):
                techs = self._parse_pipfile(content)
                technologies.extend(techs)
            
            # Node package.json
            elif file_path.endswith('package.json'):
                techs = self._parse_package_json(content)
                technologies.extend(techs)
            
            # Ruby Gemfile
            elif file_path.endswith('gemfile'):
                techs = self._parse_gemfile(content)
                technologies.extend(techs)
            
            # Java pom.xml
            elif file_path.endswith('pom.xml'):
                techs = self._parse_pom_xml(content)
                technologies.extend(techs)
            
            # Go go.mod
            elif file_path.endswith('go.mod'):
                techs = self._parse_go_mod(content)
                technologies.extend(techs)
        
        return technologies
    
    def _parse_requirements_txt(self, content: str) -> List[Technology]:
        """Parse Python requirements.txt file."""
        technologies = []
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse package==version or package>=version
            match = re.match(r'^([a-zA-Z0-9\-_]+)([=<>!]+)(.+)$', line)
            if match:
                package_name = match.group(1)
                version = match.group(3).strip()
                
                # Use intelligent classification if available
                category = self._classify_technology(package_name)
                
                tech = Technology(
                    name=package_name,
                    category=category,
                    icon=self._get_icon(package_name, category),
                    version=version,
                    latest_version=None,  # Would need API call
                    is_deprecated=False,
                    deprecation_warning=None,
                    license=None,  # Would need API call
                    vulnerabilities=[]  # Would need vulnerability DB
                )
                technologies.append(tech)
        
        return technologies
    
    def _parse_pipfile(self, content: str) -> List[Technology]:
        """Parse Python Pipfile."""
        technologies = []
        
        try:
            # Simple parsing - would use toml library in production
            lines = content.split('\n')
            in_packages = False
            
            for line in lines:
                if '[packages]' in line:
                    in_packages = True
                    continue
                elif line.startswith('[') and in_packages:
                    break
                
                if in_packages and '=' in line:
                    parts = line.split('=')
                    if len(parts) >= 2:
                        package_name = parts[0].strip()
                        version = parts[1].strip().strip('"\'')
                        
                        # Use intelligent classification if available
                        category = self._classify_technology(package_name)
                        
                        tech = Technology(
                            name=package_name,
                            category=category,
                            icon=self._get_icon(package_name, category),
                            version=version if version != '*' else None,
                            latest_version=None,
                            is_deprecated=False,
                            deprecation_warning=None,
                            license=None,
                            vulnerabilities=[]
                        )
                        technologies.append(tech)
        
        except Exception as e:
            logger.error(f"Error parsing Pipfile: {str(e)}")
        
        return technologies
    
    def _parse_package_json(self, content: str) -> List[Technology]:
        """Parse Node package.json file."""
        technologies = []
        
        try:
            data = json.loads(content)
            
            # Parse dependencies
            for dep_type in ['dependencies', 'devDependencies']:
                deps = data.get(dep_type, {})
                for package_name, version in deps.items():
                    # Clean version string
                    version_clean = version.lstrip('^~>=<')
                    
                    # Use intelligent classification if available
                    category = self._classify_technology(package_name)
                    
                    tech = Technology(
                        name=package_name,
                        category=category,
                        icon=self._get_icon(package_name, category),
                        version=version_clean,
                        latest_version=None,
                        is_deprecated=False,
                        deprecation_warning=None,
                        license=None,
                        vulnerabilities=[]
                    )
                    technologies.append(tech)
        
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing package.json: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error parsing package.json: {str(e)}")
        
        return technologies
    
    def _parse_gemfile(self, content: str) -> List[Technology]:
        """Parse Ruby Gemfile."""
        technologies = []
        
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('gem '):
                # Parse: gem 'rails', '~> 6.0'
                match = re.match(r"gem\s+['\"]([^'\"]+)['\"](?:,\s*['\"]([^'\"]+)['\"])?", line)
                if match:
                    package_name = match.group(1)
                    version = match.group(2) if match.group(2) else None
                    
                    # Use intelligent classification if available
                    category = self._classify_technology(package_name)
                    
                    tech = Technology(
                        name=package_name,
                        category=category,
                        icon=self._get_icon(package_name, category),
                        version=version.lstrip('~>= ') if version else None,
                        latest_version=None,
                        is_deprecated=False,
                        deprecation_warning=None,
                        license=None,
                        vulnerabilities=[]
                    )
                    technologies.append(tech)
        
        return technologies
    
    def _parse_pom_xml(self, content: str) -> List[Technology]:
        """Parse Java pom.xml file."""
        technologies = []
        
        # Simple regex-based parsing - would use XML parser in production
        dependency_pattern = r'<dependency>.*?<groupId>(.*?)</groupId>.*?<artifactId>(.*?)</artifactId>.*?(?:<version>(.*?)</version>)?.*?</dependency>'
        matches = re.findall(dependency_pattern, content, re.DOTALL)
        
        for match in matches:
            group_id = match[0].strip()
            artifact_id = match[1].strip()
            version = match[2].strip() if len(match) > 2 and match[2] else None
            
            tech = Technology(
                name=f"{group_id}:{artifact_id}",
                category='library',
                icon='java',
                version=version,
                latest_version=None,
                is_deprecated=False,
                deprecation_warning=None,
                license=None,
                vulnerabilities=[]
            )
            technologies.append(tech)
        
        return technologies
    
    def _parse_go_mod(self, content: str) -> List[Technology]:
        """Parse Go go.mod file."""
        technologies = []
        
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('require '):
                # Parse: require github.com/pkg/errors v0.9.1
                parts = line.replace('require ', '').split()
                if len(parts) >= 2:
                    package_name = parts[0]
                    version = parts[1]
                    
                    tech = Technology(
                        name=package_name,
                        category='library',
                        icon='go',
                        version=version,
                        latest_version=None,
                        is_deprecated=False,
                        deprecation_warning=None,
                        license=None,
                        vulnerabilities=[]
                    )
                    technologies.append(tech)
        
        return technologies
    
    def _detect_from_extensions(self, context: Dict[str, Any]) -> List[Technology]:
        """Detect languages from file extensions."""
        technologies = []
        file_summaries = context.get('file_summaries', [])
        
        # Count file extensions
        extension_counts = {}
        for f in file_summaries:
            file_path = f.get('file_path', '')
            if '.' in file_path:
                ext = file_path.split('.')[-1].lower()
                extension_counts[ext] = extension_counts.get(ext, 0) + 1
        
        # Map extensions to languages
        extension_map = {
            'py': ('Python', 'python'),
            'js': ('JavaScript', 'javascript'),
            'ts': ('TypeScript', 'typescript'),
            'jsx': ('React', 'react'),
            'tsx': ('React', 'react'),
            'java': ('Java', 'java'),
            'rb': ('Ruby', 'ruby'),
            'go': ('Go', 'go'),
            'rs': ('Rust', 'rust'),
            'php': ('PHP', 'php'),
            'cs': ('C#', 'csharp'),
            'cpp': ('C++', 'cpp'),
            'c': ('C', 'c'),
            'swift': ('Swift', 'swift'),
            'kt': ('Kotlin', 'kotlin'),
            'scala': ('Scala', 'scala'),
        }
        
        for ext, count in extension_counts.items():
            if ext in extension_map and count >= 3:  # At least 3 files
                lang_name, icon = extension_map[ext]
                tech = Technology(
                    name=lang_name,
                    category='language',
                    icon=icon,
                    version=None,
                    latest_version=None,
                    is_deprecated=False,
                    deprecation_warning=None,
                    license=None,
                    vulnerabilities=[]
                )
                technologies.append(tech)
        
        return technologies
    
    def _detect_frameworks(self, context: Dict[str, Any]) -> List[Technology]:
        """Detect frameworks from file patterns."""
        technologies = []
        file_summaries = context.get('file_summaries', [])
        file_paths = [f.get('file_path', '').lower() for f in file_summaries]
        
        # Framework detection patterns
        framework_patterns = {
            'Flask': ('flask', 'python'),
            'Django': ('django', 'python'),
            'FastAPI': ('fastapi', 'python'),
            'Express': ('express', 'javascript'),
            'React': ('react', 'react'),
            'Vue': ('vue', 'vue'),
            'Angular': ('angular', 'angular'),
            'Rails': ('rails', 'ruby'),
            'Spring': ('spring', 'java'),
            'Laravel': ('laravel', 'php'),
        }
        
        for framework, (keyword, icon) in framework_patterns.items():
            if any(keyword in path for path in file_paths):
                tech = Technology(
                    name=framework,
                    category='framework',
                    icon=icon,
                    version=None,
                    latest_version=None,
                    is_deprecated=False,
                    deprecation_warning=None,
                    license=None,
                    vulnerabilities=[]
                )
                technologies.append(tech)
        
        return technologies
    
    def _deduplicate_technologies(self, technologies: List[Technology]) -> List[Technology]:
        """Remove duplicate technologies by name (case-insensitive)."""
        seen = set()
        unique = []
        
        for tech in technologies:
            # Use lowercase name for comparison to avoid duplicates like "JavaScript" and "javascript"
            name_lower = tech.name.lower()
            if name_lower not in seen:
                seen.add(name_lower)
                unique.append(tech)
        
        return unique
    
    def _classify_technology(self, package_name: str) -> str:
        """
        Classify technology using intelligent multi-layer classification.
        
        Args:
            package_name: Name of the package
            
        Returns:
            Category string (frontend, backend, database, cache, auth, cloud, testing, ml, infra, other)
        """
        if self.classifier:
            try:
                result = self.classifier.classify(package_name)
                # classifier.classify() returns a dict with 'category' and 'legacy_category'
                # Use legacy_category for backward compatibility with frontend expectations
                category = result.get('legacy_category', result.get('category', 'other'))
                logger.debug(f"Classified {package_name} as {category}")
                return category
            except Exception as e:
                logger.warning(f"Classification failed for {package_name}: {str(e)}, using fallback")
                return self._fallback_classify(package_name)
        else:
            return self._fallback_classify(package_name)
    
    def _fallback_classify(self, package_name: str) -> str:
        """
        Fallback classification using static mapping.
        
        Args:
            package_name: Name of the package
            
        Returns:
            Category string
        """
        package_lower = package_name.lower()
        
        # Static category mapping for common packages
        # Categories: language, framework, library, database, cache, infrastructure, devops, testing, other
        category_map = {
            'framework': ['flask', 'django', 'fastapi', 'express', 'koa', 'rails', 'spring', 'react', 'vue', 'angular', 'svelte', 'next', 'nuxt', 'gatsby', 'laravel', 'symfony'],
            'database': ['sqlalchemy', 'mongoose', 'sequelize', 'typeorm', 'prisma', 'mongodb', 'postgresql', 'mysql', 'sqlite', 'mariadb'],
            'cache': ['redis', 'memcached', 'elasticache'],
            'testing': ['pytest', 'jest', 'mocha', 'jasmine', 'unittest', 'nose', 'vitest', 'cypress'],
            'library': ['axios', 'lodash', 'moment', 'dayjs', 'uuid', 'bcrypt', 'jsonwebtoken', 'dotenv', 'cors'],
            'infrastructure': ['docker', 'kubernetes', 'terraform', 'ansible', 'boto3', 'aws-sdk', 'azure-sdk', 'google-cloud'],
        }
        
        for category, keywords in category_map.items():
            if any(keyword in package_lower for keyword in keywords):
                return category
        
        # Default to library for unknown packages
        return 'library'
    
    def _get_icon(self, package_name: str, category: str = None) -> str:
        """
        Get icon identifier for a package.
        
        Args:
            package_name: Name of the package
            category: Optional category for icon selection
            
        Returns:
            Icon identifier (Simple Icons slug format: si:slug:color)
        """
        # Map common packages to Simple Icons slugs
        icon_map = {
            'flask': 'si:flask:#000000',
            'django': 'si:django:#092E20',
            'fastapi': 'si:fastapi:#009688',
            'react': 'si:react:#61DAFB',
            'vue': 'si:vuedotjs:#4FC08D',
            'angular': 'si:angular:#DD0031',
            'express': 'si:express:#000000',
            'boto3': 'si:amazonaws:#FF9900',
            'aws-sdk': 'si:amazonaws:#FF9900',
            'pytest': 'si:pytest:#0A9EDC',
            'jest': 'si:jest:#C21325',
            'numpy': 'si:numpy:#013243',
            'pandas': 'si:pandas:#150458',
            'tensorflow': 'si:tensorflow:#FF6F00',
            'pytorch': 'si:pytorch:#EE4C2C',
            'redis': 'si:redis:#DC382D',
            'mongodb': 'si:mongodb:#47A248',
            'postgresql': 'si:postgresql:#4169E1',
            'mysql': 'si:mysql:#4479A1',
            'docker': 'si:docker:#2496ED',
            'kubernetes': 'si:kubernetes:#326CE5',
            'typescript': 'si:typescript:#3178C6',
            'javascript': 'si:javascript:#F7DF1E',
            'python': 'si:python:#3776AB',
            'node': 'si:nodedotjs:#339933',
            'nextjs': 'si:nextdotjs:#000000',
            'tailwindcss': 'si:tailwindcss:#06B6D4',
        }
        
        package_lower = package_name.lower()
        
        # Check exact matches first
        if package_lower in icon_map:
            return icon_map[package_lower]
        
        # Check partial matches
        for key, icon in icon_map.items():
            if key in package_lower:
                return icon
        
        # Fallback based on category
        if category:
            category_icons = {
                'frontend': 'si:react:#61DAFB',
                'backend': 'si:nodedotjs:#339933',
                'database': 'si:database:#003B57',
                'cache': 'si:redis:#DC382D',
                'testing': 'si:pytest:#0A9EDC',
                'ml': 'si:tensorflow:#FF6F00',
                'auth': 'si:auth0:#EB5424',
                'cloud': 'si:amazonaws:#FF9900',
                'infra': 'si:docker:#2496ED'
            }
            if category in category_icons:
                return category_icons[category]
        
        # Default fallback
        return 'si:package:#888888'
    
    def _detect_versions(self, package_name: str) -> Optional[str]:
        """
        Identify version numbers.
        
        Args:
            package_name: Name of the package
            
        Returns:
            Version string if found
        """
        # This would query package registries in production
        return None
    
    def _check_vulnerabilities(self, package_name: str, version: str) -> List[Vulnerability]:
        """
        Query vulnerability databases.
        
        Args:
            package_name: Name of the package
            version: Version string
            
        Returns:
            List of vulnerabilities
        """
        # This would query vulnerability databases (e.g., OSV, NVD) in production
        return []
    
    def _identify_licenses(self, package_name: str) -> Optional[str]:
        """
        Determine license types.
        
        Args:
            package_name: Name of the package
            
        Returns:
            License string if found
        """
        # This would query package registries in production
        return None
    
    def _check_deprecation(self, package_name: str, version: str) -> tuple[bool, Optional[str]]:
        """
        Identify deprecated versions.
        
        Args:
            package_name: Name of the package
            version: Version string
            
        Returns:
            Tuple of (is_deprecated, recommended_version)
        """
        # This would check package registries in production
        return False, None
