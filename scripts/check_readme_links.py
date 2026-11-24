"""Check local Markdown links in current entry-point documentation."""
from pathlib import Path
import re, sys
root=Path(__file__).resolve().parents[1]
errors=[]
for file in ("README.md","CHANGELOG.md","CONTRIBUTING.md","SECURITY.md","docs/NATIVE-RESEARCH-CANDIDATE.md","docs/SCIENTIFIC-STATUS.md"):
    p=root/file
    for target in re.findall(r"\]\(([^)]+)\)",p.read_text()):
        if "://" in target or target.startswith("#"):continue
        path=target.split("#",1)[0]
        if path and not (p.parent/path).exists():errors.append(f"{file}: {target}")
print("\n".join(errors) if errors else "Current documentation local links OK")
sys.exit(bool(errors))
