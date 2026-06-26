import re

def clean_json_response(content: str) -> str:
    if not content:
        return ""

    content = content.strip()

    # 1. Strip thinking block
    if "</thinking>" in content:
        content = content.split("</thinking>")[-1].strip()

    # 2. Strip markdown fences
    if "```json" in content:
        start_idx = content.find("```json") + 7
        end_idx = content.rfind("```")
        if end_idx > start_idx:
            content = content[start_idx:end_idx].strip()
    elif "```" in content:
        start_idx = content.find("```") + 3
        end_idx = content.rfind("```")
        if end_idx > start_idx:
            content = content[start_idx:end_idx].strip()

    # 3. Find FIRST { or [ (outermost), and LAST } or ] (outermost closing)
    first_dict = content.find("{")
    first_list = content.find("[")

    start_idx = -1
    end_char = ""
    if first_dict != -1 and first_list != -1:
        if first_dict < first_list:
            start_idx = first_dict
            end_char = "}"
        else:
            start_idx = first_list
            end_char = "]"
    elif first_dict != -1:
        start_idx = first_dict
        end_char = "}"
    elif first_list != -1:
        start_idx = first_list
        end_char = "]"

    if start_idx != -1:
        end_idx = content.rfind(end_char)
        if end_idx != -1 and end_idx > start_idx:
            content = content[start_idx:end_idx + 1]

    # 4. Clean trailing commas
    content = re.sub(r",(\s*[}\]])", r"\1", content)

    # 5. Safety net — if still not starting with { or [
    content = content.strip()
    if content and content[0] not in ('{', '['):
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", content)
        if match:
            return match.group(1).strip()

    return content.strip()

def clean_markdown_response(content: str) -> str:
    if "```markdown" in content:
        content = content.split("```markdown")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    return content.strip()
