from pathlib import Path

# walk up rather than count parents: mutmut runs tests from a copy under backend/mutants/
REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").exists())
