# Repository contract

This repository is the reproducible source for one ORCA application image.

Public ingress is private-by-default and limited to declared OrcaHub Exposer endpoints. Secrets must never be baked into artifacts. Source may only declare `unpublished` or `qualification-pending`. Static tests are not live qualification and not publication.
