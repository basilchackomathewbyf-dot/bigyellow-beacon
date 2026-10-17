#!/usr/bin/env bash
# Apply the "POC technical design" update to the bigyellow-beacon repo.
# Usage (from the repo root, on branch develop, with a clean working tree):
#   bash /path/to/beacon-update/scripts/apply_update.sh /path/to/beacon-update
set -euo pipefail

SRC="${1:?usage: apply_update.sh /path/to/beacon-update}"
SRC="$(cd "$SRC" && pwd)"

[ -d .git ] || { echo "Run this from the repo root (the folder with .git)."; exit 1; }
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "You have uncommitted changes. Commit or stash them first (git add . && git commit -m '...')."; exit 1
fi

echo "1/5 Removing obsolete parts of the old plan"
git rm -r -q --ignore-unmatch mobile dashboards .cursor/rules/30-dashboards.mdc docs/architecture.html || true

echo "2/5 Copying contract, rules, docs, seed, scripts"
(cd "$SRC" && tar --exclude='__pycache__' --exclude='*.egg-info' --exclude='.pytest_cache' -cf - .) | tar -xf -

echo "3/5 Marking old contracts/ as legacy (deleted at the end of edge milestone M0)"
if [ -d contracts ]; then
  cat > contracts/LEGACY.md <<'EOF'
# LEGACY: do not use for new code
Replaced by `contract/beacon_contract` (see docs/DECISIONS.md §C). Kept only because the E1/E4 edge code still
imports from here. Edge milestone M0 removes these imports and deletes this folder.
EOF
fi

echo "4/5 Updating .gitignore"
touch .gitignore
for p in "certs/" "*.pem" "edge/data/" "**/.venv/" ".venv/" "node_modules/" "**/dist/" "*.egg-info/" ".pytest_cache/" "__pycache__/" ".DS_Store" ".env" "*.env"; do
  grep -qxF "$p" .gitignore || echo "$p" >> .gitignore
done

echo "5/5 Installing and testing the contract"
PY="python3"
[ -x edge/.venv/bin/python ] && PY="edge/.venv/bin/python"
"$PY" -m pip install -q -e "contract[dev]"
"$PY" -m pytest -q contract/tests

git add -A
echo
git status --short | head -60
echo
echo "Done. Review the list above, then:"
echo "  git commit -m 'Adopt POC technical design: contract v1.0, rules, plan, decisions, seed'"
echo "  git push"
