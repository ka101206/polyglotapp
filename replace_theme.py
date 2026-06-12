import os
import re

replacements = {
  'bg-slate-900': 'bg-slate-50 dark:bg-slate-900',
  'bg-slate-950': 'bg-white dark:bg-slate-950',
  'bg-slate-800': 'bg-slate-200 dark:bg-slate-800',
  'bg-slate-700': 'bg-slate-300 dark:bg-slate-700',
  'bg-slate-600': 'bg-slate-400 dark:bg-slate-600',
  'text-slate-100': 'text-slate-900 dark:text-slate-100',
  'text-slate-200': 'text-slate-800 dark:text-slate-200',
  'text-slate-300': 'text-slate-700 dark:text-slate-300',
  'text-slate-400': 'text-slate-600 dark:text-slate-400',
  'text-white': 'text-black dark:text-white',
  'border-slate-800': 'border-slate-200 dark:border-slate-800',
  'border-slate-700': 'border-slate-300 dark:border-slate-700',
  'border-slate-600': 'border-slate-400 dark:border-slate-600',
}

def process_dir(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.jsx'):
                full_path = os.path.join(root, file)
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                for old_cls, new_cls in replacements.items():
                    # Match whole words to avoid partial replacement bugs
                    pattern = r'\b' + re.escape(old_cls) + r'\b'
                    content = re.sub(pattern, new_cls, content)
                
                if content != original_content:
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"Updated {full_path}")

process_dir('/home/aboveavg/projects/polyglotapp/frontend/src')
