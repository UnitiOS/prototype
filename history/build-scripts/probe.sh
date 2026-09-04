#!/usr/bin/env bash
# Would the session's own draft seal, if valid_from had been asked for?
cd /c/Users/fareza/Desktop/Uniti/PoC || exit 1
export UNITI_DSN=postgresql://uniti:uniti@localhost:5433/uniti_check
rm -rf build/probe && mkdir -p build/probe
cp business/draft.txt build/probe/draft.txt

echo '=== 1. exactly as the session left it ==='
cp business/draft.yaml build/probe/draft.yaml
.venv/Scripts/python.exe components/seal/seal.py build/probe/draft.yaml \
    --actor probe --into build/probe/out --sealed-at 2026-01-15T09:00:00Z
echo "EXIT=$?"

echo
echo '=== 2. same draft with valid_from supplied ==='
sed 's|^  # valid_from.*|  valid_from: '"'"'2026-01-01T00:00:00Z'"'"'|' \
    business/draft.yaml > build/probe/draft.yaml
grep -n "valid_from" build/probe/draft.yaml
.venv/Scripts/python.exe components/seal/seal.py build/probe/draft.yaml \
    --actor probe --into build/probe/out --sealed-at 2026-01-15T09:00:00Z
echo "EXIT=$?"
