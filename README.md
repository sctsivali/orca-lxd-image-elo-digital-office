# ORCA LXD image template

GitHub template for one ORCA application image.

This repository starts **unpublished**. Replace the placeholders, run tests, then open a pull request. Green CI is not a published image.

## Quick start

1. Use this repository as a GitHub template
2. Edit `manifest.yaml`
3. Replace `assets/logo.png` with the official logo
4. Implement `recipes/build.sh` and `recipes/acceptance.sh`
5. Run `make validate` and `make test`
6. Open a pull request

Do not set `publication.state: published`.

## Application metadata

Replace slug, display name, version, official upstream URL, and minimum resources in `manifest.yaml`.

## OrcaHub Exposer endpoints

Declare every user-facing port. Database and admin ports stay non-public. Network default is private.

## Build lifecycle

Keep `build.ready: false` until recipes and tests are honest. Static validation does not publish the image.

## Agent instructions

Read `AGENTS.md`. You do not need Atlas-ORCA.

## License

Apache License 2.0.
