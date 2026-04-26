"""
Architecture Confidence Score Calculator

Implements a mathematically defined confidence score based on 6 weighted signals:
1. Layer Separation Score (LSS) - 25%
2. Framework Detection Score (FDS) - 15%
3. Database Integration Score (DIS) - 15%
4. Dependency Direction Score (DDS) - 20%
5. Dependency Depth Score (DDpS) - 15%
6. File Naming Consistency Score (FNCS) - 10%

Total: 100%
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ConfidenceCalculator:
    """
    Calculates architecture confidence score using weighted signals.
    
    Formula:
    Confidence = (0.25 * LSS) + (0.15 * FDS) + (0.15 * DIS) + 
                 (0.20 * DDS) + (0.15 * DDpS) + (0.10 * FNCS)
    """
    
    # Expected layers for ideal architecture
    EXPECTED_LAYERS = ["presentation", "api", "business", "data"]
    
    # Weights for each signal
    WEIGHTS = {
        'layer_separation': 0.25,
        'framework_detection': 0.15,
        'database_integration': 0.15,
        'dependency_direction': 0.20,
        'dependency_depth': 0.15,
        'naming_consistency': 0.10
    }
    
    # Known backend frameworks
    BACKEND_FRAMEWORKS = {
        'flask', 'django', 'fastapi', 'tornado', 'aiohttp', 'pyramid',
        'express', 'koa', 'hapi', 'fastify', 'nestjs',
        'rails', 'sinatra',
        'spring', 'spring-boot',
        'gin', 'echo', 'fiber',
        'actix-web', 'rocket', 'axum'
    }
    
    # Known ORMs
    KNOWN_ORMS = {
        'sqlalchemy', 'django-orm', 'peewee', 'pony',
        'sequelize', 'typeorm', 'prisma', 'mongoose', 'knex',
        'activerecord',
        'hibernate', 'jpa',
        'gorm',
        'diesel', 'sea-orm'
    }
    
    # Known databases
    KNOWN_DATABASES = {
        'postgresql', 'mysql', 'mongodb', 'redis', 'sqlite',
        'mariadb', 'cassandra', 'dynamodb', 'couchdb',
        'neo4j', 'influxdb', 'elasticsearch'
    }
    
    def calculate_confidence(
        self,
        layers: List[Any],
        tech_stack: List[Any],
        dependencies: Optional[Any],
        file_summaries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate overall architecture confidence score.
        
        Args:
            layers: Detected architecture layers
            tech_stack: Detected technologies
            dependencies: Dependency analysis result
            file_summaries: List of file summaries
            
        Returns:
            Dict containing confidence score and signal breakdown
        """
        # Calculate individual signals
        lss = self._calculate_layer_separation_score(layers)
        fds = self._calculate_framework_detection_score(tech_stack)
        dis = self._calculate_database_integration_score(tech_stack)
        dds = self._calculate_dependency_direction_score(dependencies)
        ddps = self._calculate_dependency_depth_score(dependencies)
        fncs = self._calculate_naming_consistency_score(file_summaries)
        
        # Calculate weighted confidence
        confidence = (
            self.WEIGHTS['layer_separation'] * lss +
            self.WEIGHTS['framework_detection'] * fds +
            self.WEIGHTS['database_integration'] * dis +
            self.WEIGHTS['dependency_direction'] * dds +
            self.WEIGHTS['dependency_depth'] * ddps +
            self.WEIGHTS['naming_consistency'] * fncs
        )
        
        # Clamp and round
        confidence = round(min(max(confidence, 0.0), 1.0), 2)
        
        # Log results
        logger.info(f"Confidence Score Calculation:")
        logger.info(f"  LSS (Layer Separation): {lss:.2f} (weight: {self.WEIGHTS['layer_separation']})")
        logger.info(f"  FDS (Framework Detection): {fds:.2f} (weight: {self.WEIGHTS['framework_detection']})")
        logger.info(f"  DIS (Database Integration): {dis:.2f} (weight: {self.WEIGHTS['database_integration']})")
        logger.info(f"  DDS (Dependency Direction): {dds:.2f} (weight: {self.WEIGHTS['dependency_direction']})")
        logger.info(f"  DDpS (Dependency Depth): {ddps:.2f} (weight: {self.WEIGHTS['dependency_depth']})")
        logger.info(f"  FNCS (Naming Consistency): {fncs:.2f} (weight: {self.WEIGHTS['naming_consistency']})")
        logger.info(f"  Final Confidence: {confidence:.2f}")
        
        return {
            'confidence': confidence,
            'signals': {
                'layer_separation_score': round(lss, 2),
                'framework_detection_score': round(fds, 2),
                'database_integration_score': round(dis, 2),
                'dependency_direction_score': round(dds, 2),
                'dependency_depth_score': round(ddps, 2),
                'naming_consistency_score': round(fncs, 2)
            },
            'weights': self.WEIGHTS,
            'breakdown': {
                'layer_separation': round(self.WEIGHTS['layer_separation'] * lss, 4),
                'framework_detection': round(self.WEIGHTS['framework_detection'] * fds, 4),
                'database_integration': round(self.WEIGHTS['database_integration'] * dis, 4),
                'dependency_direction': round(self.WEIGHTS['dependency_direction'] * dds, 4),
                'dependency_depth': round(self.WEIGHTS['dependency_depth'] * ddps, 4),
                'naming_consistency': round(self.WEIGHTS['naming_consistency'] * fncs, 4)
            }
        }
    
    def _calculate_layer_separation_score(self, layers: List[Any]) -> float:
        """
        Calculate Layer Separation Score (LSS).
        
        LSS = detected_layers_count / 4
        Clamp between 0 and 1
        
        Args:
            layers: List of detected layers
            
        Returns:
            LSS score (0.0-1.0)
        """
        if not layers:
            return 0.0
        
        detected_count = len(layers)
        expected_count = len(self.EXPECTED_LAYERS)
        
        lss = detected_count / expected_count
        lss = min(max(lss, 0.0), 1.0)
        
        logger.debug(f"LSS: {detected_count} layers detected / {expected_count} expected = {lss:.2f}")
        
        return lss
    
    def _calculate_framework_detection_score(self, tech_stack: List[Any]) -> float:
        """
        Calculate Framework Detection Score (FDS).
        
        FDS = 1 if known backend framework detected
        FDS = 0 otherwise
        
        Args:
            tech_stack: List of detected technologies
            
        Returns:
            FDS score (0.0 or 1.0)
        """
        if not tech_stack:
            return 0.0
        
        # Check if any technology is a known backend framework
        for tech in tech_stack:
            tech_name = tech.name.lower() if hasattr(tech, 'name') else str(tech).lower()
            
            if tech_name in self.BACKEND_FRAMEWORKS:
                logger.debug(f"FDS: Backend framework detected: {tech_name}")
                return 1.0
        
        logger.debug("FDS: No backend framework detected")
        return 0.0
    
    def _calculate_database_integration_score(self, tech_stack: List[Any]) -> float:
        """
        Calculate Database Integration Score (DIS).
        
        DIS = 1.0 if ORM + database detected
        DIS = 0.5 if database detected only
        DIS = 0.0 otherwise
        
        Args:
            tech_stack: List of detected technologies
            
        Returns:
            DIS score (0.0, 0.5, or 1.0)
        """
        if not tech_stack:
            return 0.0
        
        has_orm = False
        has_database = False
        
        for tech in tech_stack:
            tech_name = tech.name.lower() if hasattr(tech, 'name') else str(tech).lower()
            
            if tech_name in self.KNOWN_ORMS:
                has_orm = True
                logger.debug(f"DIS: ORM detected: {tech_name}")
            
            if tech_name in self.KNOWN_DATABASES:
                has_database = True
                logger.debug(f"DIS: Database detected: {tech_name}")
        
        if has_orm and has_database:
            logger.debug("DIS: ORM + Database detected = 1.0")
            return 1.0
        elif has_database:
            logger.debug("DIS: Database only detected = 0.5")
            return 0.5
        else:
            logger.debug("DIS: No database integration detected = 0.0")
            return 0.0
    
    def _calculate_dependency_direction_score(self, dependencies: Optional[Any]) -> float:
        """
        Calculate Dependency Direction Score (DDS).
        
        DDS = 1 - (circular_dependencies / total_dependencies)
        If total_dependencies == 0: DDS = 0.5
        Clamp between 0 and 1
        
        Args:
            dependencies: Dependency analysis result
            
        Returns:
            DDS score (0.0-1.0)
        """
        if not dependencies:
            logger.debug("DDS: No dependency data = 0.5")
            return 0.5
        
        # Extract circular dependencies count
        circular_deps = 0
        if hasattr(dependencies, 'circular_dependencies'):
            circular_deps = len(dependencies.circular_dependencies)
        
        # Extract total dependencies count
        total_deps = 0
        if hasattr(dependencies, 'dependency_tree') and dependencies.dependency_tree:
            if hasattr(dependencies.dependency_tree, 'total_dependencies'):
                total_deps = dependencies.dependency_tree.total_dependencies
        
        if total_deps == 0:
            logger.debug("DDS: No dependencies = 0.5")
            return 0.5
        
        dds = 1.0 - (circular_deps / total_deps)
        dds = min(max(dds, 0.0), 1.0)
        
        logger.debug(f"DDS: {circular_deps} circular / {total_deps} total = {dds:.2f}")
        
        return dds
    
    def _calculate_dependency_depth_score(self, dependencies: Optional[Any]) -> float:
        """
        Calculate Dependency Depth Score (DDpS).
        
        Ideal depth: 2 to 5
        If 2 <= depth <= 5: DDpS = 1.0
        elif depth == 1: DDpS = 0.5
        else: DDpS = max(0, 1 - (depth - 5) * 0.1)
        Clamp between 0 and 1
        
        Args:
            dependencies: Dependency analysis result
            
        Returns:
            DDpS score (0.0-1.0)
        """
        if not dependencies:
            logger.debug("DDpS: No dependency data = 0.5")
            return 0.5
        
        # Extract max depth
        depth = 0
        if hasattr(dependencies, 'dependency_tree') and dependencies.dependency_tree:
            if hasattr(dependencies.dependency_tree, 'max_depth'):
                depth = dependencies.dependency_tree.max_depth
        
        if depth == 0:
            logger.debug("DDpS: No depth data = 0.5")
            return 0.5
        
        # Calculate score based on depth
        if 2 <= depth <= 5:
            ddps = 1.0
            logger.debug(f"DDpS: Ideal depth {depth} = 1.0")
        elif depth == 1:
            ddps = 0.5
            logger.debug(f"DDpS: Shallow depth {depth} = 0.5")
        else:
            ddps = max(0.0, 1.0 - (depth - 5) * 0.1)
            logger.debug(f"DDpS: Deep depth {depth} = {ddps:.2f}")
        
        ddps = min(max(ddps, 0.0), 1.0)
        
        return ddps
    
    def _calculate_naming_consistency_score(self, file_summaries: List[Dict[str, Any]]) -> float:
        """
        Calculate File Naming Consistency Score (FNCS).
        
        FNCS = consistent_named_files / total_relevant_files
        If total_relevant_files == 0: FNCS = 0.5
        Clamp between 0 and 1
        
        Consistent naming patterns:
        - snake_case for Python
        - camelCase/PascalCase for JavaScript/TypeScript
        - kebab-case for config files
        
        Args:
            file_summaries: List of file summaries
            
        Returns:
            FNCS score (0.0-1.0)
        """
        if not file_summaries:
            logger.debug("FNCS: No files = 0.5")
            return 0.5
        
        # Filter relevant files (exclude common non-code files)
        excluded_patterns = [
            'readme', 'license', 'changelog', 'contributing',
            '.md', '.txt', '.json', '.yaml', '.yml', '.toml',
            '.gitignore', '.dockerignore', 'dockerfile',
            'package-lock', 'yarn.lock', 'poetry.lock'
        ]
        
        relevant_files = []
        for f in file_summaries:
            file_path = f.get('file_path', '').lower()
            file_name = file_path.split('/')[-1] if '/' in file_path else file_path
            
            # Skip excluded patterns
            if any(pattern in file_name for pattern in excluded_patterns):
                continue
            
            # Only include code files
            if any(file_path.endswith(ext) for ext in ['.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.java', '.rb', '.php']):
                relevant_files.append(file_path)
        
        if len(relevant_files) == 0:
            logger.debug("FNCS: No relevant files = 0.5")
            return 0.5
        
        # Check naming consistency
        consistent_count = 0
        
        for file_path in relevant_files:
            file_name = file_path.split('/')[-1]
            name_without_ext = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
            
            # Check if name follows common conventions
            is_consistent = (
                self._is_snake_case(name_without_ext) or
                self._is_camel_case(name_without_ext) or
                self._is_pascal_case(name_without_ext) or
                self._is_kebab_case(name_without_ext)
            )
            
            if is_consistent:
                consistent_count += 1
        
        fncs = consistent_count / len(relevant_files)
        fncs = min(max(fncs, 0.0), 1.0)
        
        logger.debug(f"FNCS: {consistent_count} consistent / {len(relevant_files)} relevant = {fncs:.2f}")
        
        return fncs
    
    def _is_snake_case(self, name: str) -> bool:
        """Check if name follows snake_case convention."""
        return name.islower() and '_' in name and name.replace('_', '').isalnum()
    
    def _is_camel_case(self, name: str) -> bool:
        """Check if name follows camelCase convention."""
        return name[0].islower() and name.isalnum() and any(c.isupper() for c in name)
    
    def _is_pascal_case(self, name: str) -> bool:
        """Check if name follows PascalCase convention."""
        return name[0].isupper() and name.isalnum() and any(c.isupper() for c in name[1:])
    
    def _is_kebab_case(self, name: str) -> bool:
        """Check if name follows kebab-case convention."""
        return name.islower() and '-' in name and name.replace('-', '').isalnum()
