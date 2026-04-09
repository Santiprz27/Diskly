import sys, os, ast, pathlib
sys.path.insert(0, '.')
errors = []
files = list(pathlib.Path('.').rglob('*.py'))
for f in files:
    if '__pycache__' in str(f):
        continue
    try:
        ast.parse(f.read_text(encoding='utf-8', errors='replace'))
    except SyntaxError as e:
        errors.append(f'{f}: {e}')

if errors:
    print('SYNTAX ERRORS:')
    for e in errors:
        print(' ', e)
    sys.exit(1)
else:
    count = len([f for f in files if '__pycache__' not in str(f)])
    print(f'Syntax OK - {count} files checked')
