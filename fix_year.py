import os
import re

root_dir = "."
exclude_dirs = {".venv", ".git", "__pycache__", "node_modules", "data", ".pytest_cache", "assets"}
extensions = {".md", ".html", ".py", ".js", ".json", ".txt", ".yml", ".yaml"}

replacements_made = 0
files_changed = []

pattern_num = re.compile(r'(?i)2\s*nd\s*year')
pattern_word = re.compile(r'(?i)second\s*year')

for root, dirs, files in os.walk(root_dir):
    # Modify dirs in-place to skip excluded directories
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    
    for file in files:
        ext = os.path.splitext(file)[1].lower()
        if ext in extensions or ext == "":
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                new_content = pattern_num.sub('3rd year', content)
                new_content = pattern_word.sub('third year', new_content)
                
                if new_content != content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    files_changed.append(filepath)
                    replacements_made += 1
            except Exception as e:
                pass # Skip binary or undecodable files

print(f"Files changed: {len(files_changed)}")
for f in files_changed:
    print(f" - {f}")
