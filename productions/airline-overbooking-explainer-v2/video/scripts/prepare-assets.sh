#!/usr/bin/env bash
set -euo pipefail
JOB_ID="${JOB:-airline-overbooking-explainer-v2}"
SOURCE="../../../generated-assets/${JOB_ID}/images"
DEST="assets/images"
EXPECTED=36

if [ ! -d "$SOURCE" ]; then
  echo "Missing generated image source: $SOURCE" >&2
  exit 2
fi

mkdir -p "$DEST"
rm -f "$DEST"/*.png
cp "$SOURCE"/*.png "$DEST"/
count=$(find "$DEST" -maxdepth 1 -name '*.png' | wc -l)
if [ "$count" -ne "$EXPECTED" ]; then
  echo "Expected exactly ${EXPECTED} V3 stickman images, found $count" >&2
  exit 3
fi

echo "Prepared $count V3 stickman images for ${JOB_ID}."
