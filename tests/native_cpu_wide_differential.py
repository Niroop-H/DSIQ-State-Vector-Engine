"""Reproduce the 13–20 qubit complete-vector checks from the CPU comparison."""
import argparse
import json
from pathlib import Path

from native_cpu_differential import check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    executable = parser.parse_args().executable.resolve()
    rows = []
    for width in range(13, 21):
        for real_products in (False, True):
            seed = 739251 + 100 * width + int(real_products)
            error, norm_error = check(executable, width, seed, real_products)
            rows.append(dict(n=width, seed=seed, real_products=real_products,
                             coefficients=2**width, max_abs=error, max_norm_error=norm_error))
    print(json.dumps(rows, indent=2))
    return int(any(row["max_abs"] > 1e-13 or row["max_norm_error"] > 1e-12 for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())
