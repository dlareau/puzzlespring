from pathlib import Path
import re
import os

def parse_template_comment(content):
    """Extract documentation from template comment block."""
    # Look for {% comment %} block anywhere in the file
    comment_match = re.search(r'{%\s*comment\s*%}(.*?){%\s*endcomment\s*%}', 
                           content, re.DOTALL)
    if not comment_match:
        return None
    
    comment = comment_match.group(1).strip()
    
    # Split the comment into sections based on @ symbols
    sections = re.split(r'\n\s*@', comment)
    
    # Parse the @tags
    docs = {}
    for section in sections:
        if not section.strip():
            continue
            
        # Split first line from rest of content
        lines = section.strip().split('\n')
        if not lines:
            continue
            
        # Parse the tag and its initial content
        tag_match = re.match(r'(\w+):\s*(.+)?', lines[0])
        if not tag_match:
            continue
            
        tag = tag_match.group(1)
        content_lines = []
        
        # Add first line content if it exists
        if tag_match.group(2):
            content_lines.append(tag_match.group(2))
        
        # Process remaining lines
        for line in lines[1:]:
            line = line.strip()
            if line:
                # Check for key: value format in indented lines
                sub_match = re.match(r'\s*(\w+):\s*(.+)', line)
                if sub_match and (tag in ['context', 'blocks']):
                    if tag not in docs:
                        docs[tag] = {}
                    docs[tag][sub_match.group(1)] = sub_match.group(2).strip()
                else:
                    content_lines.append(line)
        
        # Only add string content if it's not a dict section
        if content_lines and tag not in ['context', 'blocks']:
            docs[tag] = '\n'.join(content_lines).strip()
    
    return docs

def generate_template_docs():
    """Generate markdown documentation for all templates."""
    output = []
    
    # Header
    output.extend([
        "---",
        "layout: default",
        "title: Templates",
        "parent: Technical Reference",
        "nav_order: 3",
        "---",
        "",
        "# Templates",
        "",
        "This document describes the templates used in the PuzzleSpring application.",
        ""
    ])
    
    # Get all template files
    template_dir = Path('puzzlehunt/templates')
    template_files = sorted(template_dir.glob('**/*.html'))
    
    # Group templates by directory
    template_groups = {}
    for template_path in template_files:
        dir_name = template_path.parent.name
        if dir_name == 'templates':
            dir_name = 'root'
            
        if dir_name not in template_groups:
            template_groups[dir_name] = []
            
        with open(template_path, 'r') as f:
            content = f.read()
            docs = parse_template_comment(content)
            if docs:
                template_groups[dir_name].append((template_path.name, docs))
    
    # Process templates by directory
    # Sort directories but ensure 'root' comes first
    sorted_dirs = sorted(template_groups.items(), 
                        key=lambda x: ('z' if x[0] != 'root' else '', x[0]))
    
    for dir_name, templates in sorted_dirs:
        if templates:  # Only show directories with documented templates
            output.extend([
                f"## {dir_name.replace('_', ' ').title()}",
                ""
            ])
            
            for template_name, docs in templates:
                output.extend([
                    f"### <u>{template_name}</u>",
                    ""
                ])
                
                if 'description' in docs:
                    output.extend([
                        "_Description:_ " + docs['description'],
                        "",
                        ""
                    ])
                
                if 'extends' in docs:
                    output.extend([
                        "_Extends:_ " + docs['extends'],
                        "",
                        ""
                    ])
                
                if 'context' in docs:
                    output.extend([
                        "_Context Variables:_",
                        ""
                    ])
                    for var_name, description in docs['context'].items():
                        output.append(f"- `{var_name}`: {description}")
                    output.extend(["", ""])
                
                if 'blocks' in docs:
                    output.extend([
                        "_Template Blocks:_",
                        ""
                    ])
                    for block_name, description in docs['blocks'].items():
                        output.append(f"- `{block_name}`: {description}")
                    output.extend(["", ""])
                
                output.append("")
    
    # Write to file
    docs_path = "website/docs/technical-reference/templates.md"
    os.makedirs(os.path.dirname(docs_path), exist_ok=True)
    with open(docs_path, "w") as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    generate_template_docs() 