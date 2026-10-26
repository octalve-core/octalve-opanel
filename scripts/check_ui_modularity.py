"""Guard against monolithic OPanel screens, while allowing small components.

Run: python scripts/check_ui_modularity.py
UI pages must be compositions, not 1000-line forms/monolithic dashboards.
Treat this limit as a design budget: extract a hook, module, form or section
instead of suppressing it. Backend business logic should likewise live in
scoped adapter/policy modules and be validated by independent tests.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "frontend" / "src"
MAX_COMPONENT_LINES = 200
MAX_ROUTE_LINES = 100


def main():
    checked, failures = 0, []
    for pattern, limit in [
        ("components/**/*.tsx", MAX_COMPONENT_LINES),
        ("app/**/page.tsx", MAX_ROUTE_LINES),
    ]:
        for file in ROOT.glob(pattern):
            if not file.is_file():
                continue
            checked += 1
            lines = len(file.read_text(encoding="utf-8").splitlines())
            if lines > limit:
                failures.append(f"{file.relative_to(ROOT)}: {lines} lines (limit {limit})")
    if failures:
        for failure in failures:
            print("MODULARITY FAIL", failure)
        return 1
    if checked < 12:
        print("MODULARITY FAIL: expected OPanel screens are missing.")
        return 1
    print(f"MODULARITY PASS: {checked} screens/components within audited limits.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
