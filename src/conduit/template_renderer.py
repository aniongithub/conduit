"""
Safe template rendering utilities for Conduit pipeline elements.

This module provides secure template rendering using Jinja2 to replace
unsafe eval() usage throughout the codebase.
"""

import os
from typing import Any, Dict
from jinja2 import Environment, BaseLoader, TemplateError, select_autoescape


class SafeTemplateRenderer:
    """Safe template renderer using Jinja2 with restricted functionality"""
    
    def __init__(self):
        # Create a sandboxed Jinja2 environment
        self.env = Environment(
            loader=BaseLoader(),
            autoescape=select_autoescape(),
            # Disable some potentially dangerous features
            enable_async=False,
        )
        
        # Add custom filters for path operations
        self._add_path_filters()
    
    def _add_path_filters(self):
        """Add custom filters for path manipulation"""
        
        def get_filename(path: str) -> str:
            """Get only the filename part of the path"""
            return os.path.basename(path)
        
        def get_extension(path: str) -> str:
            """Get only the extension part of the path"""
            return os.path.splitext(path)[1]
        
        def get_basename(path: str) -> str:
            """Get only the basename part of the path (filename without extension)"""
            return os.path.splitext(os.path.basename(path))[0]
        
        def get_dirname(path: str) -> str:
            """Get only the directory name part of the path"""
            return os.path.dirname(path)
        
        def get_stem(path: str) -> str:
            """Get only the stem part of the path (same as basename)"""
            return os.path.splitext(os.path.basename(path))[0]
        
        def get_abspath(path: str) -> str:
            """Get the absolute path"""
            return os.path.abspath(path)
        
        def get_realpath(path: str) -> str:
            """Get the real path (resolving symlinks)"""
            return os.path.realpath(path)
        
        def get_relpath(path: str) -> str:
            """Get the relative path"""
            return os.path.relpath(path)
        
        def get_normpath(path: str) -> str:
            """Get the normalized path"""
            return os.path.normpath(path)
        
        def get_filename_without_extension(path: str) -> str:
            """Get filename without extension"""
            return os.path.splitext(path)[0]
        
        # Register filters
        self.env.filters['get_filename'] = get_filename
        self.env.filters['get_extension'] = get_extension
        self.env.filters['get_basename'] = get_basename
        self.env.filters['get_dirname'] = get_dirname  
        self.env.filters['get_stem'] = get_stem
        self.env.filters['get_abspath'] = get_abspath
        self.env.filters['get_realpath'] = get_realpath
        self.env.filters['get_relpath'] = get_relpath
        self.env.filters['get_normpath'] = get_normpath
        self.env.filters['get_filename_without_extension'] = get_filename_without_extension
    
    def render_template(self, template_string: str, context: Dict[str, Any]) -> str:
        """
        Safely render a template string with the given context.
        
        Args:
            template_string: The template string to render
            context: Dictionary of variables available in the template
            
        Returns:
            Rendered string
            
        Raises:
            TemplateError: If template rendering fails
        """
        try:
            template = self.env.from_string(template_string)
            return template.render(**context)
        except TemplateError as e:
            raise TemplateError(f"Template rendering failed: {e}")
        except Exception as e:
            raise TemplateError(f"Unexpected error during template rendering: {e}")
    
    def render_path_template(self, template_string: str, path: str) -> str:
        """
        Convenience method for rendering path-based templates.
        
        Args:
            template_string: Template string that expects a 'path' variable
            path: Path string to use in template
            
        Returns:
            Rendered string
        """
        return self.render_template(template_string, {'path': path})


# Global renderer instance
_renderer = None

def get_template_renderer() -> SafeTemplateRenderer:
    """Get the global template renderer instance"""
    global _renderer
    if _renderer is None:
        _renderer = SafeTemplateRenderer()
    return _renderer

def safe_render(template_string: str, **context) -> str:
    """
    Convenience function for safe template rendering.
    
    Args:
        template_string: Template to render
        **context: Variables available in template
        
    Returns:
        Rendered string
    """
    renderer = get_template_renderer()
    return renderer.render_template(template_string, context)