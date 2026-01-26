"""Self-modification system for Clanker robot.

This module allows the AI to read, analyze, and modify its own code.
"""

import ast
import os
import inspect
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from utils.logger import setup_logger

logger = setup_logger(__name__)


class CodeAnalyzer:
    """Analyzes Python code using AST."""
    
    def __init__(self):
        self.analyzed_files: Dict[str, ast.AST] = {}
    
    def parse_file(self, filepath: str) -> Optional[ast.AST]:
        """Parse a Python file into an AST."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                code = f.read()
            tree = ast.parse(code)
            self.analyzed_files[filepath] = tree
            return tree
        except Exception as e:
            logger.error(f"Failed to parse {filepath}: {e}")
            return None
    
    def find_functions(self, tree: ast.AST) -> List[Dict]:
        """Find all function definitions in AST."""
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    'name': node.name,
                    'line': node.lineno,
                    'args': [arg.arg for arg in node.args.args],
                    'docstring': ast.get_docstring(node)
                })
        
        return functions
    
    def find_classes(self, tree: ast.AST) -> List[Dict]:
        """Find all class definitions in AST."""
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                classes.append({
                    'name': node.name,
                    'line': node.lineno,
                    'methods': methods,
                    'docstring': ast.get_docstring(node)
                })
        
        return classes
    
    def analyze_code_quality(self, tree: ast.AST) -> Dict:
        """Analyze code quality metrics."""
        functions = self.find_functions(tree)
        classes = self.find_classes(tree)
        
        # Count complexity (simplified)
        complexity = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.Try)):
                complexity += 1
        
        return {
            'function_count': len(functions),
            'class_count': len(classes),
            'complexity': complexity,
            'functions': functions,
            'classes': classes
        }


class SelfModifier:
    """System for self-modification of robot code."""
    
    def __init__(self, project_root: str = "."):
        """
        Initialize self-modifier.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.analyzer = CodeAnalyzer()
        self.modification_history: List[Dict] = []
        self.enabled = True
        
        logger.info("Self-modification system initialized")
    
    def analyze_self(self) -> Dict:
        """Analyze the robot's own codebase."""
        analysis = {
            'files': {},
            'total_functions': 0,
            'total_classes': 0
        }
        
        # Find all Python files
        python_files = list(self.project_root.rglob("*.py"))
        
        for filepath in python_files:
            # Skip __pycache__ and virtual environments
            if '__pycache__' in str(filepath) or 'venv' in str(filepath):
                continue
            
            rel_path = str(filepath.relative_to(self.project_root))
            tree = self.analyzer.parse_file(str(filepath))
            
            if tree:
                quality = self.analyzer.analyze_code_quality(tree)
                analysis['files'][rel_path] = quality
                analysis['total_functions'] += quality['function_count']
                analysis['total_classes'] += quality['class_count']
        
        logger.info(f"Self-analysis complete: {analysis['total_functions']} functions, {analysis['total_classes']} classes")
        return analysis
    
    def find_optimization_opportunities(self) -> List[Dict]:
        """Find potential code optimizations."""
        opportunities = []
        analysis = self.analyze_self()
        
        for filepath, quality in analysis['files'].items():
            # Check for high complexity
            if quality['complexity'] > 20:
                opportunities.append({
                    'file': filepath,
                    'type': 'high_complexity',
                    'severity': 'medium',
                    'description': f"High complexity ({quality['complexity']}) detected"
                })
            
            # Check for large functions (simplified - would need line counting)
            if quality['function_count'] == 0 and quality['class_count'] > 0:
                opportunities.append({
                    'file': filepath,
                    'type': 'no_functions',
                    'severity': 'low',
                    'description': "File has classes but no standalone functions"
                })
        
        return opportunities
    
    def create_behavior_file(self, behavior_name: str, behavior_code: str) -> bool:
        """
        Create a new behavior file.
        
        Args:
            behavior_name: Name of the behavior
            behavior_code: Python code for the behavior
            
        Returns:
            True if successful
        """
        if not self.enabled:
            logger.warning("Self-modification is disabled")
            return False
        
        try:
            behavior_dir = self.project_root / "ai" / "behaviors"
            behavior_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = behavior_dir / f"{behavior_name.lower()}.py"
            
            # Validate code before writing
            try:
                ast.parse(behavior_code)
            except SyntaxError as e:
                logger.error(f"Invalid Python syntax in behavior code: {e}")
                return False
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(behavior_code)
            
            self.modification_history.append({
                'type': 'create_behavior',
                'file': str(filepath),
                'timestamp': str(Path(__file__).stat().st_mtime)
            })
            
            logger.info(f"Created new behavior file: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create behavior file: {e}")
            return False
    
    def modify_function(self, filepath: str, function_name: str, new_code: str) -> bool:
        """
        Modify an existing function with improved boundary detection and backup.
        """
        if not self.enabled:
            logger.warning("Self-modification is disabled")
            return False
        
        try:
            full_path = self.project_root / filepath
            if not full_path.exists():
                logger.error(f"File not found: {filepath}")
                return False
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            tree = ast.parse(content)
            target_node = None
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    target_node = node
                    break
            
            if target_node is None:
                logger.error(f"Function {function_name} not found in {filepath}")
                return False
            
            # Find end of function more accurately
            start_line = target_node.lineno - 1
            end_line = target_node.end_lineno if hasattr(target_node, 'end_lineno') else start_line + len(target_node.body) + 1
            
            # Prepare new content
            new_lines = lines[:start_line] + [new_code] + lines[end_line:]
            new_content = '\n'.join(new_lines)
            
            # Validate final syntax
            try:
                ast.parse(new_content)
            except SyntaxError as e:
                logger.error(f"Modification results in invalid Python syntax: {e}")
                return False
            
            # Backup
            backup_path = full_path.with_suffix('.py.backup')
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Write changes
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            self.modification_history.append({
                'type': 'modify_function',
                'file': filepath,
                'function': function_name,
                'timestamp': str(time.time())
            })
            
            logger.info(f"Successfully modified function {function_name} in {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to modify function: {e}", exc_info=True)
            return False

    def rollback(self, filepath: str) -> bool:
        """Rollback a file to its .backup version."""
        try:
            full_path = self.project_root / filepath
            backup_path = full_path.with_suffix('.py.backup')
            if backup_path.exists():
                os.replace(backup_path, full_path)
                logger.info(f"Rolled back {filepath}")
                return True
            return False
        except Exception as e:
            logger.error(f"Rollback failed for {filepath}: {e}")
            return False
    
    def get_modification_history(self) -> List[Dict]:
        """Get history of self-modifications."""
        return self.modification_history.copy()
    
    def disable(self):
        """Disable self-modification (safety feature)."""
        self.enabled = False
        logger.warning("Self-modification disabled")
    
    def enable(self):
        """Enable self-modification."""
        self.enabled = True
        logger.info("Self-modification enabled")
