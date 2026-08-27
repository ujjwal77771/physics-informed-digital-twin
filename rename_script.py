import os
import re

files_to_update = ['README.md', 'index.html', 'frontend/App.js']

replacements = {
    r'(?i)\bIMS\b': 'NASA C-MAPSS',
    r'(?i)\bbearing prognostics\b': 'Turbofan Engine Prognostics',
    r'(?i)\bbearing health\b': 'Engine Health',
    r'(?i)industrial bearing\b': 'industrial turbofan engine',
    r'(?i)bearing lifecycle\b': 'engine lifecycle',
    r'(?i)\bbearings\b': 'engines',
    r'(?i)\bbearing\b': 'engine'
}

for filepath in files_to_update:
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        new_content = content
        for pattern, replacement in replacements.items():
            # Use a function to preserve case of original match where possible, or just force the replacement string case
            # Since the replacement strings are specific, we'll just use them directly, but maybe fix capitalization for 'engine'
            new_content = re.sub(pattern, replacement, new_content)
            
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")
