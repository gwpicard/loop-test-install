## The loop
This project uses AI Loop Kit. Pieces are GitHub issues with one `state:` label.
Only the gate (gate.py) changes a state label. The person merges every pull request.
Prepare command: `python3 -m venv .venv && .venv/bin/pip install pytest && ([ ! -f pyproject.toml ] || .venv/bin/pip install -e '.[test]')`
Test command: `python -m coverage run -m pytest`
Quality: `python3 "$AI_LOOP_KIT_ROOT/quality/mutmut-changed.py" origin/main`
Quality: `python -m coverage run -m pytest && coverage json -o coverage.json && python3 "$AI_LOOP_KIT_ROOT/quality/crap.py" --coverage coverage.json --base origin/main`
Standards: `STANDARDS.md`
Protected paths: `AGENTS.md, STANDARDS.md, .github`
Agent: codex
