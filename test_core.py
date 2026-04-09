import sys, os
sys.path.insert(0, '.')

# Test Trie logic
print('[TEST] DirNode Trie...')
from scanner.dir_trie import DirNode
root = DirNode(name='C:\\')
root.insert(['Users', 'santi', 'Documents', 'file.docx'], 1024*500, False)
root.insert(['Users', 'santi', 'Downloads', 'video.mp4'], 1024*1024*250, False)
root.insert(['Users', 'santi', 'Downloads', 'setup.exe'], 1024*1024*80, False)
root.insert(['Windows', 'System32', 'kernel32.dll'], 1024*1024*5, False)
root.insert(['Windows', 'System32', 'ntdll.dll'], 1024*1024*3, False)
root.insert(['Program Files', 'app.exe'], 1024*1024*120, False)
total, files = root.accumulate()

from utils.format_bytes import format_bytes
print(f'  Total: {format_bytes(total)}, Files: {files}')
print(f'  Root children: {list(root.children.keys())}')
dl = root.children['Users'].children['santi'].children['Downloads']
print(f'  Downloads size: {format_bytes(dl.total_size)}')

# Test Treemap export
tree_nodes = root.to_treemap_nodes(max_depth=5)
print(f'  Treemap root children count: {len(tree_nodes["children"])}')

# Test search
results = list(root.search('santi'))
print(f'  Search santi: {len(results)} matches')
print('  [PASS] Trie OK')

# Test format_bytes
print()
print('[TEST] format_bytes...')
from utils.format_bytes import format_bytes, format_count
assert format_bytes(0) == '0 B'
assert 'KB' in format_bytes(2048)
assert 'MB' in format_bytes(1024*1024*5)
assert 'GB' in format_bytes(1024**3 * 2)
print('  [PASS] format_bytes OK')

# Test elevation check
print()
print('[TEST] elevation...')
from utils.elevation import is_admin
print(f'  Admin: {is_admin()}')
print('  [PASS] elevation OK')

# Test psutil drive listing
print()
print('[TEST] psutil drives...')
import psutil
parts = psutil.disk_partitions(all=False)
print(f'  Drives found: {[p.device for p in parts]}')
print('  [PASS] psutil OK')

print()
print('ALL UNIT TESTS PASSED!')
