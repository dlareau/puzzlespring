#!/usr/bin/env python3

import sass
import os
from pathlib import Path

def compile_scss(input_file: str, output_file: str):
    """Compile a SCSS file to CSS."""
    try:
        # Get the directory of the input file to properly resolve imports
        input_dir = os.path.dirname(input_file)
        
        # Read the input file
        with open(input_file, 'r') as f:
            scss_content = f.read()
        
        # Compile the SCSS
        css_content = sass.compile(
            string=scss_content,
            include_paths=[input_dir]
        )
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Write the compiled CSS
        with open(output_file, 'w') as f:
            f.write(css_content)
            
        print(f"Successfully compiled {input_file} to {output_file}")
        
    except Exception as e:
        print(f"Error compiling {input_file}: {str(e)}")

def main():
    # Get the project root directory (2 levels up from scripts/)
    project_root = Path(__file__).parent.parent
    
    # Define input and output files
    scss_files = [
        {
            'input': 'puzzlehunt/styles/custom/base_bulma.scss',
            'output': 'puzzlehunt/static/base_bulma.css'
        },
        {
            'input': 'puzzlehunt/styles/custom/hunt_bulma.scss',
            'output': 'puzzlehunt/static/hunt_bulma.css'
        }
    ]
    
    # Compile each file
    for file_info in scss_files:
        input_path = project_root / file_info['input']
        output_path = project_root / file_info['output']
        compile_scss(str(input_path), str(output_path))

if __name__ == '__main__':
    main() 