from __future__ import annotations

import re


def section_heading_present(content: str, section: str) -> bool:
    name = section.strip()
    if not name:
        return False
    pattern = rf"^#{{2,3}}\s+{re.escape(name)}\s*$"
    return re.search(pattern, content, re.M) is not None


def run_format_check(content: str, required_sections: list[str]) -> dict:
    required = list(dict.fromkeys(s.strip() for s in required_sections if s.strip()))
    present = [s for s in required if section_heading_present(content, s)]
    missing = [s for s in required if s not in present]
    return {"ok": len(missing) == 0, "required": required, "present": present, "missing": missing}
