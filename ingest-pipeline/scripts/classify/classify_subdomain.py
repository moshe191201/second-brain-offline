#!/usr/bin/env python3
"""Thin wrapper for subdomain classification — delegates to judge.py."""
import sys

if __name__ == "__main__":
    try:
        from judge import main
    except ImportError:
        from scripts.classify.judge import main  # type: ignore
    sys.exit(main())
