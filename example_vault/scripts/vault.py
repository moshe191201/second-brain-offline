#!/usr/bin/env python3
"""Vault CLI shim — framework-owned, do not edit.

The real implementation lives in the installed `second-brain-vault-framework`
package, so a vault can never drift from the framework that built it. This file
exists only so `python3 scripts/vault.py <cmd>` works from inside a vault
without needing the `vault` entry point on PATH.

    pip install --upgrade second-brain-vault-framework
"""
import sys

try:
    from second_brain_vault_framework.cli import main
except ImportError:  # pragma: no cover - environment guidance path
    sys.exit(
        "vault: the second-brain-vault-framework package is not installed in this\n"
        "       interpreter. Install it, then re-run:\n\n"
        "         pip install --upgrade second-brain-vault-framework\n\n"
        "       Air-gapped: install from the internal index — see instructions.md,\n"
        "       'Distribution & updates'.\n"
    )

if __name__ == "__main__":
    sys.exit(main())
