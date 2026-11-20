#!/usr/bin/env sh
# Copy to scripts/run-all.sh, then replace example paths with manifest entries.
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_root"

printf '%s\n' 'Running Python preparation'
python3 scripts/python/01_prepare.py

printf '%s\n' 'Running R analysis'
Rscript scripts/R/02_analyze.R

printf '%s\n' 'Compiling Fortran model'
mkdir -p build
gfortran -O2 -Wall -Wextra -o build/model scripts/fortran/model.f90

printf '%s\n' 'Running Fortran model'
./build/model

printf '%s\n' 'Pipeline complete'
