#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
elo-digital-office build recipe is not executable yet.

This image cannot be built from a public GitHub release. ELO 25 Server Setup
media is vendor-supplied and must be mounted read-only by a maintainer.

Intended later steps (do not run against a shared lab from this script):

1. Start from Ubuntu 24.04 virtual-machine.
2. Install PostgreSQL bound to 127.0.0.1 only.
3. Copy operator-supplied Server Setup media into guest-owned storage.
4. Hash the installer entrypoint before and after the copy.
5. Launch Server Setup on guest loopback port 7458.
6. Stop before license apply, archive apply, and Web Client install.
7. Generate first-boot credentials. Never bake .pk, passwords, or host keys.

build.ready remains false until those steps are implemented with a
deterministic, unprivileged recipe and tests.
EOF

exit 0
