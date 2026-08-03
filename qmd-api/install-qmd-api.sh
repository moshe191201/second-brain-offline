#!/usr/bin/env bash
# Install the pre-built qmd install tree into the user's global npm prefix.
#
# This is the gap-side half of QMD-API-STAGING.md: the tarball was produced on a
# connected staging machine whose OS, CPU arch, and Node major version match this
# one, so the compiled native modules (better-sqlite3, sqlite-vec) already work.
# Nothing here compiles, downloads, or reaches the network.
#
#   ./install-qmd-api.sh qmd-install-tree.tgz
#
# Verify-only (checks an existing install without touching it):
#
#   ./install-qmd-api.sh --verify
#
set -euo pipefail

TARBALL="${1:-qmd-install-tree.tgz}"
VERIFY_ONLY=0
[[ "${1:-}" == "--verify" ]] && { VERIFY_ONLY=1; TARBALL=""; }

die() { printf '\nqmd-api: %s\n' "$*" >&2; exit 1; }
step() { printf '\n==> %s\n' "$*"; }

command -v node >/dev/null || die "node not found on PATH."
command -v npm  >/dev/null || die "npm not found on PATH."

NPM_PREFIX="$(npm prefix -g)"
NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"

step "Environment"
echo "  node        $(node --version)  (major $NODE_MAJOR)"
echo "  npm prefix  $NPM_PREFIX"

if [[ $VERIFY_ONLY -eq 0 ]]; then
  [[ -f "$TARBALL" ]] || die "tarball '$TARBALL' not found. Pass its path as the first argument."

  step "Extracting $TARBALL into $NPM_PREFIX"
  # The tree was packed with `tar czf ... -C "$(npm prefix -g)" .`, so it unpacks
  # relative to the prefix — bin/ and lib/node_modules/ land where npm expects them.
  tar xzf "$TARBALL" -C "$NPM_PREFIX"
fi

step "Checking the qmd binary"
command -v qmd >/dev/null || die "qmd is not on PATH. Add '$NPM_PREFIX/bin' to PATH and re-run --verify."
echo "  qmd $(qmd --version)"

step "Checking native modules load under this Node ABI"
# A mismatch here is the 'compiled against a different Node.js version' failure —
# it means the staging machine's Node major did not match this one.
QMD_DIR="$(npm ls -g --parseable @tobilu/qmd 2>/dev/null | tail -1)"
[[ -n "$QMD_DIR" ]] || QMD_DIR="$NPM_PREFIX/lib/node_modules/@tobilu/qmd"
node -e "require('$QMD_DIR/node_modules/better-sqlite3'); console.log('  better-sqlite3 OK')" \
  || die "better-sqlite3 failed to load. Re-stage on a machine running Node $NODE_MAJOR.x."

step "Next steps"
cat <<'EOF'
  Set the backend env vars machine-wide (see QMD-API-STAGING.md for the full list):

    QMD_LLM=openai
    QMD_OPENAI_BASE_URL=https://<internal-endpoint>/v1
    QMD_OPENAI_EMBED_MODEL=<embeddings model name>
    QMD_OPENAI_CHAT_MODEL=<chat model name>

  Model names must match the endpoint's /v1/models list exactly, tag suffix included.
  Then verify and register:

    qmd doctor                          # the "openai backend" check must be green
    python3 scripts/vault.py register   # from inside your vault
EOF
