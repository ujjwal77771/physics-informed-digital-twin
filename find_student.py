import os
import re

root_dir = "."
exclude_dirs = {".venv", ".git", "__pycache__", "node_modules", "data", "assets"}
extensions = {".md", ".html", ".py", ".js", ".json", ".txt"}

for root, dirs, files in os.walk(root_dir):
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    for file in files:
        ext = os.path.splitext(file)[1].lower()
        if ext in extensions or ext == "":
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                if re.search(r'(?i)student', content):
                    print(f"Found in {filepath}")
            except Exception:
                pass
