"""DirNode Trie — efficient hierarchical size accumulation.

Design:
  - Each DirNode represents a file or directory.
  - insert() builds the tree from path components.
  - accumulate() post-order propagates sizes up.
  - to_dataframe() exports to Plotly-ready DataFrame with numeric IDs.
    Returns (df, id_map) where id_map[str_id] → path_parts from root.
  - top_files() returns the N heaviest files in this subtree (heap-based, O(n log k)).
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Iterator
import pandas as pd


@dataclass
class DirNode:
    name: str
    size: int = 0          # raw size (own files only, not children)
    file_count: int = 0    # direct file count
    is_dir: bool = True
    children: dict[str, "DirNode"] = field(default_factory=dict)

    # Filled by accumulate()
    total_size: int = 0
    total_files: int = 0

    # ------------------------------------------------------------------ #
    # Insertion
    # ------------------------------------------------------------------ #

    def insert(self, path_parts: list[str], size: int, is_dir: bool) -> None:
        """Insert a path entry into the trie (optimized iterative version)."""
        if not path_parts:
            return
        node = self
        for i, part in enumerate(path_parts):
            if part not in node.children:
                node.children[part] = DirNode(name=part)
            node = node.children[part]
        node.size += size
        node.is_dir = is_dir
        if not is_dir:
            node.file_count += 1

    # ------------------------------------------------------------------ #
    # Accumulation (post-order)
    # ------------------------------------------------------------------ #

    def accumulate(self) -> tuple[int, int]:
        """Recursively accumulate total_size and total_files. Returns (total_size, total_files)."""
        self.total_size = self.size
        self.total_files = self.file_count
        for child in self.children.values():
            cs, cf = child.accumulate()
            self.total_size += cs
            self.total_files += cf
        return self.total_size, self.total_files

    @staticmethod
    def build_from_flat_entries(root_name: str, entries: dict[int, tuple[int, str, bool, int]]) -> DirNode:
        """High-performance tree construction from a flat map of FRNs.
        
        Args:
            root_name: Name for the root node (e.g., 'C:\\')
            entries: Map of {frn: (parent_frn, name, is_dir, size)}
        """
        ROOT_FRN = 5
        nodes: dict[int, DirNode] = {ROOT_FRN: DirNode(name=root_name)}
        
        # 1. Create all nodes first
        for frn, (parent_frn, name, is_dir, size) in entries.items():
            if frn == ROOT_FRN: continue
            node = DirNode(name=name)
            node.is_dir = is_dir
            node.size = size
            if not is_dir:
                node.file_count = 1
            nodes[frn] = node
            
        # 2. Link nodes to their parents
        for frn, (parent_frn, name, is_dir, size) in entries.items():
            if frn == ROOT_FRN: continue
            if parent_frn in nodes:
                parent_node = nodes[parent_frn]
                node = nodes[frn]
                parent_node.children[name] = node
                
        return nodes[ROOT_FRN]

    # ------------------------------------------------------------------ #
    # Tree Export for Squarified Algorithm
    # ------------------------------------------------------------------ #

    def to_treemap_nodes(self, max_depth: int = 4) -> dict:
        """Convert the trie subtree to a hierarchical dictionary.
        
        Returns a dict suitable for utils.squarify.compute_treemap().
        Filters out nodes < 0.5% of parent size at depth > 0 to keep UI snappy.
        """
        return self._collect_tree([], 0, max_depth)

    def _collect_tree(self, path_parts: list[str], depth: int, max_depth: int) -> dict:
        node_dict = {
            "name": self.name,
            "size": self.total_size,
            "is_dir": self.is_dir,
            "path_parts": path_parts,
            "children": []
        }
        
        if depth >= max_depth or not self.children:
            return node_dict
            
        sorted_children = sorted(
            self.children.values(), key=lambda n: n.total_size, reverse=True
        )
        
        min_size = self.total_size * 0.005  # 0.5% size threshold
        
        others_size = 0
        others_count = 0
        
        for c in sorted_children:
            if c.total_size >= min_size:
                child_path = path_parts + [c.name]
                node_dict["children"].append(c._collect_tree(child_path, depth + 1, max_depth))
            else:
                others_size += c.total_size
                others_count += 1
                
        if others_size > 0:
            node_dict["children"].append({
                "name": f"+{others_count} más",
                "size": others_size,
                "is_dir": True,
                "path_parts": None,  # Not navigable
                "children": []
            })
            
        return node_dict

    # ------------------------------------------------------------------ #
    # Top N heaviest files  (heap-based — O(n log k))
    # ------------------------------------------------------------------ #

    def top_files(self, n: int = 10) -> list[tuple[str, int, list[str]]]:
        """Return the N heaviest files in this subtree.

        Returns list of (filename, size_bytes, path_parts) sorted by size desc.
        path_parts is relative to this node.
        """
        heap: list[tuple[int, int, str, list[str]]] = []  # (size, uid, name, parts)
        uid = [0]
        self._collect_files_heap(heap, [], n, uid)
        results = [(name, size, parts) for size, _, name, parts in heap]
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def _collect_files_heap(
        self,
        heap: list,
        path_parts: list[str],
        n: int,
        uid: list,
    ) -> None:
        for name, child in self.children.items():
            child_path = path_parts + [name]
            if not child.is_dir and child.size > 0:
                uid[0] += 1
                entry = (child.size, uid[0], name, child_path)
                if len(heap) < n:
                    heapq.heappush(heap, entry)
                elif child.size > heap[0][0]:
                    heapq.heapreplace(heap, entry)
            # Always recurse into dirs (even if dir entry itself is small)
            if child.children:
                child._collect_files_heap(heap, child_path, n, uid)

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #

    def get_node(self, path_parts: list[str]) -> "DirNode | None":
        """Navigate to a node given relative path parts."""
        if not path_parts:
            return self
        head, *tail = path_parts
        child = self.children.get(head)
        if child is None:
            return None
        return child.get_node(tail)

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #

    def search(self, query: str, max_results: int = 200) -> list["DirNode"]:
        """Return nodes whose name contains query (case-insensitive), up to max_results."""
        return [node for node, _ in self.search_with_paths(query, max_results)]

    def search_with_paths(
        self, query: str, max_results: int = 200
    ) -> list[tuple["DirNode", list[str]]]:
        """Return (node, path_parts) pairs for nodes matching query.

        path_parts is the absolute path from this node's children downward,
        so it can be passed directly to TreemapView.navigate_to().
        Results are sorted by size descending.
        """
        q = query.lower()
        results: list[tuple[DirNode, list[str]]] = []
        self._search_paths_recursive(q, results, max_results, [])
        results.sort(key=lambda x: x[0].total_size, reverse=True)
        return results

    def _search_paths_recursive(
        self,
        q: str,
        results: list,
        max_results: int,
        path: list[str],
    ) -> None:
        if len(results) >= max_results:
            return
        for name, child in self.children.items():
            if len(results) >= max_results:
                return
            child_path = path + [name]
            if q in name.lower():
                results.append((child, child_path))
            child._search_paths_recursive(q, results, max_results, child_path)

    def __repr__(self) -> str:
        from utils.format_bytes import format_bytes
        return (
            f"DirNode(name={self.name!r}, "
            f"total={format_bytes(self.total_size)}, "
            f"children={len(self.children)})"
        )
