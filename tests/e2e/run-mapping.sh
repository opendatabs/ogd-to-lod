#!/usr/bin/env bash
# Run a local YARRRML mapping → RDF (observations.ttl).
#
# Usage: tests/e2e/run-mapping.sh <results-folder>
#
# The folder must contain:
#   - mapping.yarrrml.yaml  (with the {CSV_SOURCE} placeholder)
#   - data.csv              (the source data, always named data.csv by the
#                            --local writer)
#
# The script copies the folder's `data.csv` into a temp work-dir, substitutes
# the YARRRML's {CSV_SOURCE} placeholder with `data.csv`, runs yarrrml-parser
# + RMLMapper via Docker, and writes observations.ttl back into
# <results-folder>.

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <results-folder>" >&2
  exit 1
fi

FOLDER="$1"
if [[ ! -d "$FOLDER" ]]; then
  echo "Error: not a directory: $FOLDER" >&2
  exit 1
fi

MAPPING="$FOLDER/mapping.yarrrml.yaml"
if [[ ! -f "$MAPPING" ]]; then
  echo "Error: missing mapping.yarrrml.yaml in $FOLDER" >&2
  exit 1
fi

CSV_SRC="$FOLDER/data.csv"
if [[ ! -f "$CSV_SRC" ]]; then
  echo "Error: missing data.csv in $FOLDER" >&2
  exit 1
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Git Bash/MSYS rewrites POSIX paths in CLI args (e.g. /data/*),
# which breaks container-internal paths passed to docker.
is_msys=false
case "${OSTYPE:-}" in
  msys*|cygwin*) is_msys=true ;;
esac

WORK_MOUNT="$WORK"
if [[ "$is_msys" == "true" ]]; then
  if command -v cygpath >/dev/null 2>&1; then
    WORK_MOUNT="$(cygpath -m "$WORK")"
  fi
fi

# Substitute the {CSV_SOURCE} placeholder with "data.csv".
sed 's|{CSV_SOURCE}|data.csv|g' "$MAPPING" > "$WORK/mapping.yarrrml.yaml"
cp "$CSV_SRC" "$WORK/data.csv"

YARRRML_IMAGE="${YARRRML_IMAGE:-rmlio/yarrrml-parser:latest}"
RMLMAPPER_IMAGE="${RMLMAPPER_IMAGE:-rmlio/rmlmapper-java:latest}"

echo "→ yarrrml-parser: mapping.yarrrml.yaml → mapping.ttl"
if [[ "$is_msys" == "true" ]]; then
  MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' docker run --rm --platform linux/amd64 \
    -v "$WORK_MOUNT:/data" \
    "$YARRRML_IMAGE" \
    -i /data/mapping.yarrrml.yaml \
    -o /data/mapping.ttl
else
  docker run --rm --platform linux/amd64 \
    -v "$WORK_MOUNT:/data" \
    "$YARRRML_IMAGE" \
    -i /data/mapping.yarrrml.yaml \
    -o /data/mapping.ttl
fi

echo "→ RMLMapper: mapping.ttl + data.csv → observations.ttl"
if [[ "$is_msys" == "true" ]]; then
  MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' docker run --rm --platform linux/amd64 \
    -v "$WORK_MOUNT:/data" \
    "$RMLMAPPER_IMAGE" \
    -m /data/mapping.ttl \
    -o /data/observations.ttl \
    -s turtle
else
  docker run --rm --platform linux/amd64 \
    -v "$WORK_MOUNT:/data" \
    "$RMLMAPPER_IMAGE" \
    -m /data/mapping.ttl \
    -o /data/observations.ttl \
    -s turtle
fi

cp "$WORK/observations.ttl" "$FOLDER/observations.ttl"
echo "✓ Wrote: $FOLDER/observations.ttl"
