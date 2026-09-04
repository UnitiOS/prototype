#!/usr/bin/env bash
# Does the first real session's draft pass the contract? Copies only.
cd /c/Users/fareza/Desktop/Uniti/PoC || exit 1
export UNITI_DSN=postgresql://uniti:uniti@localhost:5433/uniti_check
rm -rf build/t && mkdir -p build/t/in build/t/out
cp business/draft.yaml business/draft.txt build/t/in/

echo '=== 1. as the session left it ==='
.venv/Scripts/python.exe components/seal/seal.py build/t/in/draft.yaml \
    --actor test --into build/t/out --sealed-at 2026-01-15T09:00:00Z
echo "EXIT=$?"

echo
echo '=== 2. same draft, with the one missing answer supplied ==='
python - <<'EOF'
p = "build/t/in/draft.yaml"
s = open(p, encoding="utf-8").read()
s = s.replace("  transcript: draft.txt",
              "  transcript: draft.txt\n  valid_from: '2026-08-01T00:00:00Z'")
open(p, "w", encoding="utf-8").write(s)
EOF
.venv/Scripts/python.exe components/seal/seal.py build/t/in/draft.yaml \
    --actor test --into build/t/out --sealed-at 2026-01-15T09:00:00Z
echo "EXIT=$?"

echo
echo '=== what landed in the log ==='
.venv/Scripts/python.exe -c "
from components.kernel.perform import connect
Q='''select e_s.id, a.value_literal, a.value_ref is not null
     from assertion a join entity e_s on e_s.id=a.subject_id
     where a.intent_id=(select intent_id from assertion order by seq desc limit 1)
     order by a.seq'''
with connect() as c:
    for sid, val, ref in c.execute(Q).fetchall():
        print(f'  {str(val)[:60]:<60} ref={ref}')
"
echo
echo '=== did the comment survive the seal? ==='
grep -c "belum ditanyakan" build/t/out/v1.yaml || echo "  0 - comments gone"
