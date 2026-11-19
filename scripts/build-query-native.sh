#!/bin/sh
# Optional Linux/GCC native contraction helpers. No network or paid services.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
out=${1:-"$root/.dsiq-native"}
mkdir -p "$out"
cc=${CC:-gcc}
"$cc" -O3 -shared -fPIC -fno-fast-math "$root/native/region_dp.c" -o "$out/region_dp.so" -lm
"$cc" -O3 -shared -fPIC -fno-fast-math "$root/native/quad_center.c" -o "$out/quad_center.so" -lquadmath -lm
printf 'export DSIQ_REGION_DP_LIBRARY="%s/region_dp.so"\nexport DSIQ_QUAD_LIBRARY="%s/quad_center.so"\n' "$out" "$out"
