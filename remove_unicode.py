#!/usr/bin/env python
"""Remove all Unicode characters from Python files"""
import re
from pathlib import Path

# Map of Unicode to ASCII
replacements = {
    '[OK]': '[OK]',
    '[DONE]': '[DONE]',
    '[ERROR]': '[ERROR]',
    '[BRAIN]': '[BRAIN]',
    '*': '*',
}

# Process all Python files
for py_file in Path('.').rglob('*.py'):
    try:
        content = py_file.read_text(encoding='utf-8')
        original = content
        
        for unicode_char, ascii_replacement in replacements.items():
            content = content.replace(unicode_char, ascii_replacement)
        
        if content != original:
            py_file.write_text(content, encoding='utf-8')
            print(f'[FIXED] {py_file.name}')
        else:
            print(f'[SKIP]  {py_file.name}')
    except Exception as e:
        print(f'[ERROR] {py_file.name}: {e}')

print('\nDone!')
