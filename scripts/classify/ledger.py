"""Ledger helpers — append-only JSONL projection (shared with calibrate.py).

Exported as scripts/classify/ledger.py for explicit import.
Works when run as `python scripts/classify/ledger.py` or when imported as package.
"""
try:
    from scripts.classify.calibrate import ledger_append, ledger_project
except ImportError:
    try:
        from calibrate import ledger_append, ledger_project  # when CWD is scripts/classify
    except ImportError:
        # Fallback: import via importlib when invoked directly
        import importlib.util
        from pathlib import Path
        _spec = importlib.util.spec_from_file_location("classify_calibrate", Path(__file__).with_name("calibrate.py"))
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)  # type: ignore
        ledger_append = _mod.ledger_append  # type: ignore
        ledger_project = _mod.ledger_project  # type: ignore

__all__ = ["ledger_append", "ledger_project"]
