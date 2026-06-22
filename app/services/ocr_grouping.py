from typing import List, Dict, Tuple
from app.services.ocr_engine import OCRFragment

def group_by_line(
    fragments: List[OCRFragment], 
    start_line_idx: int = 1, 
    threshold: float = 12.0
) -> Tuple[str, Dict[int, List[OCRFragment]], int]:
    """
    Group fragments on a page into lines based on Y coordinate centers.
    
    Args:
        fragments: List of OCRFragment.
        start_line_idx: The starting index for line numbering.
        threshold: Max Y-center distance (in pixels) to group fragments into the same line.
        
    Returns:
        lines_string: Formatted text lines for the LLM.
        line_fragment_map: Mapping of line index to its constituent fragments.
        next_line_idx: The next line index to be used for subsequent pages.
    """
    if not fragments:
        return "", {}, start_line_idx

    # Sort fragments top-to-bottom by Y-center first
    def get_y_center(frag: OCRFragment) -> float:
        bbox = frag["bbox"]
        return (bbox[1] + bbox[3]) / 2.0

    sorted_fragments = sorted(fragments, key=get_y_center)

    grouped_lines: List[List[OCRFragment]] = []

    for frag in sorted_fragments:
        y_center = get_y_center(frag)
        
        # Try to find a group/line that has a close Y-center average
        placed = False
        for line_group in grouped_lines:
            avg_y = sum(get_y_center(f) for f in line_group) / len(line_group)
            if abs(y_center - avg_y) <= threshold:
                line_group.append(frag)
                placed = True
                break
        
        if not placed:
            grouped_lines.append([frag])

    # Now, sort the lines themselves top-to-bottom by average Y center
    grouped_lines = sorted(grouped_lines, key=lambda g: sum(get_y_center(f) for f in g) / len(g))

    lines_string_parts = []
    line_fragment_map = {}
    current_line_idx = start_line_idx

    for line_group in grouped_lines:
        # Sort fragments in this line left-to-right (X ascending)
        sorted_line = sorted(line_group, key=lambda f: f["bbox"][0])
        
        # Concatenate text values
        concatenated_text = " ".join(f["text"] for f in sorted_line)
        
        # Calculate Y-center for display
        avg_y = int(sum(get_y_center(f) for f in sorted_line) / len(sorted_line))
        
        # Format string line
        line_str = f'Line {current_line_idx}  [y:{avg_y}]: "{concatenated_text}"'
        lines_string_parts.append(line_str)
        
        # Store in mapping
        line_fragment_map[current_line_idx] = sorted_line
        current_line_idx += 1

    lines_string = "\n".join(lines_string_parts)
    return lines_string, line_fragment_map, current_line_idx
