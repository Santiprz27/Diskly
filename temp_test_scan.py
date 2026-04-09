import logging
logging.basicConfig(level=logging.INFO)
from scanner.mft_scanner import scan_drive
from scanner.dir_trie import DirNode

def test_scan(drive='C', admin=False):
    root = DirNode(name=f"{drive}:\\")
    count = 0
    for parts, size, is_dir in scan_drive(drive, admin=admin):
        if parts:
            root.insert(parts, size, is_dir)
        count += 1
        if count % 100000 == 0:
            print('processed', count)
    root.accumulate()
    print('Entries:', count)
    print('Root children count:', len(root.children))
    print('Root total size:', root.total_size)
    for i, (name, node) in enumerate(root.children.items()):
        if i >= 5:
            break
        print('Child', name, 'size', node.total_size, 'is_dir', node.is_dir)

if __name__ == '__main__':
    test_scan('C', admin=True)
