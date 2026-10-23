# ELO Digital Office

Unpublished ORCA application image source for ELO 25 Server Setup.

This repository starts **unpublished**. Green CI is source-ready only.
Maintainer live qualification on a disposable Ubuntu VM is
**qualification-pending**. It is not a published catalog image, not a lab snapshot,
and not a finished document Web Client.

Follow the public contributor guide:
https://github.com/sctsivali/orca-image-contributor-guide

## Application

ELO Digital Office is a proprietary ECM. Each customer uses a different
vendor license. This source therefore stops at **Server Setup**:

- Ubuntu 24.04 virtual machine
- local PostgreSQL on the guest loopback
- vendor Server Setup media staged by the operator
- 80 GiB root disk (QCOW2 virtual size; do not launch at 40 GiB)
- wizard listener on guest `127.0.0.1:7458` only; do not bind `0.0.0.0`
- no baked `.pk` license, master password, archive admin password, or
  machine identity

Tenants finish the wizard themselves and apply **their own** license later.
Do not copy a lab VM that already contains a not-for-resale entitlement.

## OrcaHub Exposer endpoints

Network default is **private**. This Server Setup-only image declares **one**
HTTP port:

| Name | Port | Default public | Role |
|---|---|---|---|
| `setup` | 7458 | no | Server Setup wizard on `127.0.0.1` |

Later application and administration consoles are not declared here. They are
not listening until the tenant finishes Server Setup. Do not auto-publish them
from OrcaHub checkout.

PostgreSQL (`5432`) and search (`9200`) stay undeclared and non-public.

Reach the wizard with a host-loopback LXD proxy plus SSH forward, or a
first-boot helper **after** tenant unlock. Do not bind the wizard to `0.0.0.0`
to make Expose Services green.

Public Exposer ingress, if a maintainer later enables it, does not make the
instance itself public.

## Build lifecycle

`build.ready` is **false**. The vendor installer is not a public GitHub
release, so this repository cannot fetch it deterministically.

Required static checks:

```bash
python3 -m pip install -r requirements-dev.txt
make validate
make test
```

Live LXD qualification: **passed** on a disposable maintainer VM
(20 Oct 2026). The candidate is not on `images.orca.id` and is not
listed on `inventory.orca.id`. Shared Sivali lab capacity is
maintainer-only. Do not treat any internal candidate alias as
downloadable.

Intended later maintainer build (not publication):

1. Mount operator-supplied ELO 25 Server Setup media read-only.
2. Install PostgreSQL on guest loopback only.
3. Copy installer bytes into guest-owned storage and hash the entrypoint.
4. Start Server Setup on loopback `7458`.
5. Stop before license apply, `rest/apply`, and Web Client deployment.
6. Generate first-boot credentials. Never bake secrets.

## How to use after a future published release

Use the immutable alias from the verified release catalog. Do not treat any
internal candidate alias as downloadable today.

1. Launch the VM on a private network with an 80 GiB root disk and the
   persistent paths attached. A 40 GiB volume is smaller than the image
   virtual size and LXD will refuse it.
2. Open the `setup` endpoint path `/` only after a local HTTP readiness check
   on `127.0.0.1:7458`. Bare `/` may return 404; use the current Server Setup
   session URL from installer logs on the operator machine. Do not bind
   that listener to `0.0.0.0`.
3. Unlock Server Setup with a first-boot password, not a baked lab password.
4. Apply the tenant license file. Do not reuse another tenant's `.pk`.
5. Add Web Client in Applications only after the tenant archive exists.

## Persistence

- `/opt/elo` — vendor program and archive
- `/var/lib/postgresql` — database
- `/var/lib/elo-setup` — installer state (no secrets in Git)

## License and branding

Source license is Apache-2.0. ELO itself remains proprietary vendor software.
`assets/logo.png` is a raster of the official ELO wordmark from
https://www.elo.com/typo3conf/ext/nelo_elocom_templates/Resources/Public/Images/logo_elo.svg.

## Agent instructions

Read `AGENTS.md`. You do not need Atlas-ORCA.

Keep `publication.state: unpublished`.
