"""Compare per-ID results; a closed scientific gate never means eligible."""
import json, os, sys
from pathlib import Path
def read(path):
    d=json.loads(Path(path).read_text())
    rows=d["results"]
    ids=[r["id"] for r in rows]
    if len(ids)!=105 or set(ids)!=set(range(1,106)):
        raise ValueError("Missing or duplicate Diamond IDs")
    statuses={"PASS","PARTIAL","FAIL","BLOCKED","NOT_RUN"}
    if any(r["status"] not in statuses for r in rows):
        raise ValueError("Unknown status")
    counts={s:sum(r["status"]==s for r in rows) for s in statuses}
    if d["counts"]!=counts or d["releaseEligible"]!=(counts["PASS"]==105):
        raise ValueError("Inconsistent scientific report")
    return d,{r["id"]:r["status"] for r in rows}
old,a=read(sys.argv[1])
new,b=read(sys.argv[2])
changes=[dict(id=i,previous=a[i],current=b[i]) for i in sorted(a) if a[i]!=b[i]]
# Incomparable incomplete states are flagged for review, not silently improved.
rank={"PASS":3,"PARTIAL":2,"FAIL":1,"BLOCKED":1,"NOT_RUN":0}
regressions=[r for r in changes if rank[r["current"]]<rank[r["previous"]] or (r["current"]=="FAIL" and r["previous"]!="FAIL")]
outcome=os.environ.get("GATE_OUTCOME")
if outcome and outcome!=("success" if new["releaseEligible"] else "failure"):
    raise ValueError("Runner outcome disagrees with scientific report")
print(json.dumps(dict(baseline=old["counts"],current=new["counts"],changes=changes,regressions=regressions,releaseEligible=new["releaseEligible"]),indent=2))
sys.exit(bool(regressions))
