import json
import os

notebook_path = r'c:\Users\clair\Desktop\Final Project\reviewdata\cleaned_reviewdata.ipynb'

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

found = False
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = "".join(cell['source'])
        if 'konlpy.jvm.init_jvm' in source:
            # Fix 1: init_jvm args -> max_heap_size
            new_source = source.replace(
                "konlpy.jvm.init_jvm(jvmpath=None, args=['-Xmx8g'])",
                "konlpy.jvm.init_jvm(max_heap_size=8192)"
            )
            # Fix 2: Twitter constructor parameter
            new_source = new_source.replace(
                "twitter = Twitter(max_heap_size=8192)",
                "twitter = Twitter()"
            )
            
            # Update the cell source (as a list of lines for notebook format)
            cell['source'] = [line + '\n' for line in new_source.split('\n')]
            if cell['source'][-1] == '\n':
                cell['source'].pop()
            else:
                # Clean up if the split/join added an extra newline or missed one
                cell['source'] = [line if line.endswith('\n') else line + '\n' for line in new_source.splitlines()]
                # Standardize to have \n at end of each line except maybe the last, 
                # but notebook format usually prefers \n at the end of each line in the list.
                cell['source'] = [line + '\n' for line in new_source.splitlines()]
                # Adjust last line
                if cell['source'] and cell['source'][-1].endswith('\n'):
                    cell['source'][-1] = cell['source'][-1].rstrip('\n')
            
            found = True
            break

if found:
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print("Notebook updated successfully.")
else:
    print("Target code not found in notebook.")
