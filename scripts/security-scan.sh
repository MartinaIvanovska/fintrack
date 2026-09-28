#!/usr/bin/env bash
# Run the security scanners and save their reports to security-reports/.
#
#   bandit     static analysis of backend/app for common Python security issues
#   pip-audit  known vulnerabilities in the backend's pinned runtime dependencies
#   npm audit  known vulnerabilities in the frontend's dependencies
#
# Usage:  ./scripts/security-scan.sh [--report-only]
#         (needs backend/.venv from setup-venv.sh and frontend/node_modules from npm ci)
#
# Exit code:
#   0  no findings (or --report-only and every scanner produced its report)
#   1  findings were reported (without --report-only)
#   2  a scanner failed to run or produced no readable report

set -uo pipefail

REPORT_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --report-only) REPORT_ONLY=1 ;;
    -h|--help) sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$REPO_ROOT/security-reports"
VENV_BIN="$REPO_ROOT/backend/.venv/bin"
PYTHON="$VENV_BIN/python"
mkdir -p "$OUT"
rm -f "$OUT"/*.json

findings=0   # a scanner reported something
broken=0     # a scanner didn't produce a readable report
summary=""   # markdown for the GitHub job summary

# section <title> <summary text> <parser exit code>
section() {
  while IFS= read -r line; do echo "    $line"; done <<< "$2"
  summary+=$'\n'"**$1**"$'\n\n```\n'"$2"$'\n```\n'
  if [ "$3" -ne 0 ]; then
    echo "    !! no readable report - the scanner itself failed" >&2
    broken=1
  fi
}

echo "==> bandit (backend/app)"
( cd "$REPO_ROOT/backend" && "$VENV_BIN/bandit" -r app -c pyproject.toml -f json -o "$OUT/bandit.json" -q ) || findings=1
text=$("$PYTHON" - "$OUT/bandit.json" <<'EOF'
import json, sys
results = json.load(open(sys.argv[1]))["results"]
for r in results:
    print(f"{r['issue_severity']} {r['test_id']} {r['issue_text']} ({r['filename']}:{r['line_number']})")
print(f"{len(results)} issue(s)")
EOF
); section "Bandit" "$text" $?

echo "==> pip-audit (backend/requirements.txt)"
"$VENV_BIN/pip-audit" -r "$REPO_ROOT/backend/requirements.txt" --progress-spinner off -f json -o "$OUT/pip-audit.json" >/dev/null 2>&1 || findings=1
text=$("$PYTHON" - "$OUT/pip-audit.json" <<'EOF'
import json, sys
deps = json.load(open(sys.argv[1]))["dependencies"]
for d in deps:
    ids = sorted({v["id"] for v in d.get("vulns", [])})
    if ids:
        print(f"{d['name']} {d['version']}: {len(ids)} advisories")
print(f"{sum(len({v['id'] for v in d.get('vulns', [])}) for d in deps)} advisories in {len(deps)} packages")
EOF
); section "pip-audit" "$text" $?

echo "==> npm audit (frontend)"
( cd "$REPO_ROOT/frontend" && npm audit --json > "$OUT/npm-audit.json" 2>/dev/null ) || findings=1
text=$("$PYTHON" - "$OUT/npm-audit.json" <<'EOF'
import json, sys
counts = json.load(open(sys.argv[1]))["metadata"]["vulnerabilities"]
print(", ".join(f"{k}: {v}" for k, v in counts.items() if v and k != "total") + f" (total {counts['total']})")
EOF
); section "npm audit" "$text" $?

if [ $broken -eq 1 ]; then
  status=2
elif [ $findings -eq 1 ] && [ $REPORT_ONLY -eq 0 ]; then
  status=1
else
  status=0
fi

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  {
    echo "### Security scan"
    [ $REPORT_ONLY -eq 1 ] && echo "Report-only: findings are listed here and in the \`security-reports\` artifact; they don't fail the build."
    echo "$summary"
  } >> "$GITHUB_STEP_SUMMARY"
fi

echo "==> reports written to security-reports/ (findings: $findings, report-only: $REPORT_ONLY, exit code $status)"
exit $status
