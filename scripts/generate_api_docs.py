from django.urls import get_resolver, URLPattern, URLResolver
import inspect
import os
from django.apps import apps

def get_view_docs(view_func):
    """Extract documentation from a view function."""
    docstring = inspect.getdoc(view_func) or "No description available."
    
    # Get parameters from function signature
    sig = inspect.signature(view_func)
    params = []
    for name, param in sig.parameters.items():
        if name not in ['request', 'args', 'kwargs']:
            params.append(f"- `{name}`: {param.annotation.__name__ if param.annotation != inspect._empty else 'any'}")
    
    return docstring, params

def get_all_view_patterns(urlpatterns, base_path=''):
    """Recursively get all URL patterns."""
    patterns = []
    
    # Paths to exclude
    excluded_paths = [
        'admin/',
        'accounts/',  # allauth urls
        'impersonate/',
        '__debug__/',
    ]
    
    for pattern in urlpatterns:
        if isinstance(pattern, URLResolver):
            # Skip entire URL namespaces we want to exclude
            pattern_str = str(pattern.pattern)
            if any(pattern_str.startswith(excluded) for excluded in excluded_paths):
                continue
                
            # Handle included URLconfs
            new_base = base_path + str(pattern.pattern)
            patterns.extend(get_all_view_patterns(pattern.url_patterns, new_base))
        elif isinstance(pattern, URLPattern):
            if pattern.callback:
                # Add the full path to the pattern
                full_path = base_path + str(pattern.pattern)
                patterns.append((full_path, pattern.callback))
    
    return patterns

def generate_api_docs():
    """Generate markdown documentation for all API endpoints."""
    output = []
    
    # Header
    output.extend([
        "---",
        "layout: default",
        "title: API Reference",
        "parent: Technical Reference",
        "nav_order: 1",
        "---",
        "",
        "# API Reference",
        "",
        "This document describes the available API endpoints in PuzzleSpring.",
        ""
    ])

    # Get all URL patterns recursively
    resolver = get_resolver()
    all_patterns = get_all_view_patterns(resolver.url_patterns)
    
    # Group views by module and function
    view_groups = {}
    
    for pattern, view_func in all_patterns:
        module_name = view_func.__module__.split('.')[-1]
        func_name = view_func.__name__
        
        if module_name not in view_groups:
            view_groups[module_name] = {}
            
        if func_name not in view_groups[module_name]:
            view_groups[module_name][func_name] = {
                'func': view_func,
                'patterns': []
            }
            
        view_groups[module_name][func_name]['patterns'].append(pattern)

    # Process views by module
    for module_name, views in sorted(view_groups.items()):
        if module_name.startswith('admin') or module_name.startswith('debug'):
            continue
            
        output.extend([
            f"## {module_name.replace('_', ' ').title()}",
            ""
        ])

        for func_name, view_info in sorted(views.items()):
            if not func_name.startswith('_'):
                docstring, params = get_view_docs(view_info['func'])
                
                output.extend([
                    f"### <u>{func_name}</u>",
                    "",
                    f"_Description:_ {docstring}",
                    "",
                    "_URL Patterns:_",
                ])
                
                # Add all URL patterns for this view
                for pattern in sorted(view_info['patterns']):
                    output.append(f"- `{pattern}`")
                
                if params:
                    output.extend([
                        "",
                        "_Parameters:_",
                        *params,
                    ])
                
                output.append("")

    # Write to file
    docs_path = "website/docs/technical-reference/api-reference.md"
    os.makedirs(os.path.dirname(docs_path), exist_ok=True)
    with open(docs_path, "w") as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    import django
    django.setup()
    generate_api_docs() 