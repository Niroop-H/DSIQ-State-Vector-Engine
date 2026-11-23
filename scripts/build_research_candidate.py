"""Build a deterministic source archive for the verified native CPU paths."""
import argparse
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "docs/NATIVE-RESEARCH-CANDIDATE.md": "README.md",
    "benchmarks/global/WIDE.md": "benchmarks/global/WIDE.md",
    "benchmarks/global/wide_statevector.py": "benchmarks/global/wide_statevector.py",
    "benchmarks/global/excitation_check.py": "benchmarks/global/excitation_check.py",
    "native/bond_contract.py": "native/bond_contract.py",
    "native/excitation_statevector.py": "native/excitation_statevector.py",
    "native/mps_exact.py": "native/mps_exact.py",
}

def build(output):
    contents = {target: (ROOT / source).read_bytes() for source,target in FILES.items()}
    contents["requirements.txt"] = b"numpy==2.3.5\n"
    checks = [f"{hashlib.sha256(data).hexdigest()}  {name}\n"
              for name,data in sorted(contents.items())]
    contents["SHA256SUMS"] = "".join(checks).encode()
    with zipfile.ZipFile(output,"w") as archive:
        for name,data in sorted(contents.items()):
            entry = zipfile.ZipInfo(name, date_time=(1980,1,1,0,0,0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry,data)
    return hashlib.sha256(output.read_bytes()).hexdigest()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    output = parser.parse_args().output
    print(f"{build(output)}  {output.name}")
