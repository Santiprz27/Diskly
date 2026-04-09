"""Squarified Treemap Algorithm.

A pure Python implementation of the Squarified Treemap algorithm
(Bruls, Huizing, van Wijk, 2000) for generating padded rectangles.
"""

from typing import List, Dict, Any, Tuple

def normalize_sizes(items: List[Dict[str, Any]], target_area: float) -> List[Dict[str, Any]]:
    """Scale the 'size' of each item so their sum equals target_area."""
    total_size = sum(item["size"] for item in items)
    if total_size <= 0:
        return []
        
    multiplier = target_area / total_size
    normalized = []
    for item in items:
        new_item = item.copy()
        new_item["area"] = item["size"] * multiplier
        normalized.append(new_item)
        
    return normalized

def _worst_ratio(row: List[Dict[str, Any]], w: float) -> float:
    """Calculate the worst aspect ratio of a row of items within length w."""
    if not row:
        return float("inf")
        
    areas = [item["area"] for item in row]
    sum_area = sum(areas)
    if sum_area == 0 or w == 0:
        return float("inf")
        
    w_squared = w * w
    max_area = max(areas)
    min_area = min(areas)
    
    return max(
        (w_squared * max_area) / (sum_area * sum_area),
        (sum_area * sum_area) / (w_squared * min_area)
    )

def _layout_row(row: List[Dict[str, Any]], x: float, y: float, w: float, h: float) -> Tuple[List[Dict[str, Any]], float, float, float, float]:
    """Layout a row of items in the current rectangle and return the leftover rect."""
    sum_area = sum(item["area"] for item in row)
    
    laid_out = []
    if w >= h:
        # Lay out vertically along the left edge
        row_width = sum_area / h if h > 0 else 0
        current_y = y
        for item in row:
            node_h = item["area"] / row_width if row_width > 0 else 0
            new_node = item.copy()
            new_node["rect"] = (x, current_y, row_width, node_h)
            laid_out.append(new_node)
            current_y += node_h
        
        # Leftover rect
        return laid_out, x + row_width, y, w - row_width, h
    else:
        # Lay out horizontally along the top edge
        row_height = sum_area / w if w > 0 else 0
        current_x = x
        for item in row:
            node_w = item["area"] / row_height if row_height > 0 else 0
            new_node = item.copy()
            new_node["rect"] = (current_x, y, node_w, row_height)
            laid_out.append(new_node)
            current_x += node_w
            
        # Leftover rect
        return laid_out, x, y + row_height, w, h - row_height

def squarify(items: List[Dict[str, Any]], x: float, y: float, w: float, h: float) -> List[Dict[str, Any]]:
    """Squarify a list of items into the bounding box (x, y, w, h).
    
    Items must be a list of dicts, sorted descending by 'area'.
    Returns the same list with a 'rect' key added: (x, y, w, h).
    """
    children = items[:]
    laid_out = []
    current_row = []
    
    while children:
        child = children[0]
        
        if not current_row:
            current_row.append(child)
            children.pop(0)
            continue
            
        # Current length of the shortest side
        shortest_side = min(w, h)
        
        # Try adding to row
        ratio_current = _worst_ratio(current_row, shortest_side)
        ratio_with_child = _worst_ratio(current_row + [child], shortest_side)
        
        if ratio_current >= ratio_with_child:
            # Aspect ratio improved or stayed the same, add it
            current_row.append(child)
            children.pop(0)
        else:
            # It got worse, layout the current row and start entirely fresh
            row_laid_out, x, y, w, h = _layout_row(current_row, x, y, w, h)
            laid_out.extend(row_laid_out)
            current_row = []

    # Layout any remaining items in the last row
    if current_row:
        row_laid_out, x, y, w, h = _layout_row(current_row, x, y, w, h)
        laid_out.extend(row_laid_out)
        
    return laid_out

def squarify_dirnode(node: Any, x: float, y: float, w: float, h: float, depth: int = 0, pad: float = 2.0, path_parts: List[str] = None) -> List[Dict[str, Any]]:
    """Compute squarified geometry directly from a DirNode.
    
    Culls recursion dynamically based on pixel size (w<2 or h<2) to allow 
    infinite depth without crashing, similar to WizTree.
    """
    if path_parts is None:
        path_parts = []
        
    box = {
        "rect": (x, y, w, h),
        "name": node.name,
        "is_dir": node.is_dir,
        "depth": depth,
        "size": node.total_size,
        "node": node,  # reference for navigation
        "path_parts": path_parts
    }
    flat_list = [box]
    
    if depth > 12 or w <= 3 or h <= 3 or not node.is_dir or not node.children:
        return flat_list
        
    inner_x = x + pad
    inner_y = y + pad
    inner_w = w - (pad * 2)
    inner_h = h - (pad * 2)
    
    HEADER_HEIGHT = 16
    if inner_h > HEADER_HEIGHT + pad:
        inner_y += HEADER_HEIGHT
        inner_h -= HEADER_HEIGHT
        
    if inner_w <= 2 or inner_h <= 2:
        return flat_list
        
    children = [c for c in node.children.values() if c.total_size > 0]
    children.sort(key=lambda c: c.total_size, reverse=True)
    
    tot = sum(c.total_size for c in children)
    if tot == 0:
        return flat_list
        
    # Normalize to area
    items = []
    ratio = (inner_w * inner_h) / tot
    for c in children:
        items.append({"node": c, "area": c.total_size * ratio})
        
    laid_out = squarify(items, inner_x, inner_y, inner_w, inner_h)
    
    for item in laid_out:
        cx, cy, cw, ch = item["rect"]
        c_node = item["node"]
        
        # Pixel culling: Stop deep recursion if the visual size is too tiny
        if cw < 3 and ch < 3:
            flat_list.append({
                "rect": (cx, cy, cw, ch),
                "name": c_node.name,
                "is_dir": c_node.is_dir,
                "depth": depth + 1,
                "size": c_node.total_size,
                "node": c_node,
                "path_parts": path_parts + [c_node.name]
            })
        else:
            flat_list.extend(squarify_dirnode(c_node, cx, cy, cw, ch, depth + 1, pad, path_parts + [c_node.name]))
            
    return flat_list
