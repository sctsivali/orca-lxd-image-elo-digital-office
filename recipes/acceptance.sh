#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
elo-digital-office acceptance is not a live LXD run.

Static validation must pass without LXD. Shared Sivali lab capacity is
maintainer-only.

When a qualifier later runs this image, acceptance must prove:

- Server Setup answers on guest loopback 7458 (bare GET / may be 404)
- PostgreSQL listens on 127.0.0.1:5432 only
- no .pk license, private key, or baked password on the root filesystem
- hostname and machine identity are not lab-specific
- Web Client is absent until the tenant applies their own license
- live LXD result labeled passed or failed, never implied by CI

Current live LXD result: passed (maintainer disposable VM, 20 Oct 2026).
Not a catalog publication. Not a lab snapshot.
EOF

exit 0
