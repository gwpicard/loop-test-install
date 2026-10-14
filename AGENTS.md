## The loop
This project uses AI Loop Kit. Pieces are GitHub issues with one `state:` label.
Only the gate (gate.py) changes a state label. The person merges every pull request.
Prepare command: `python3 -m venv .venv && .venv/bin/pip install -e '.[test]'`
Test command: `python -m pytest`
