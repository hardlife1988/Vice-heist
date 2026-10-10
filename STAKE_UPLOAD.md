# Vice Heist — Stake upload guide

**Current release instructions:** [PRODUCTION_HANDOFF.md](PRODUCTION_HANDOFF.md).

This file previously described the early demo-only frontend and obsolete RTP measurements. That guidance is superseded by the current feature-branch RGS integration and production CI.

## Submission status

- **Not submitted, deployed, certified, or approved by Stake.**
- The automated production pipeline builds `release/math/` and `release/frontend/` separately and checks production math, 104 million weighted outcome samples, browser mock-RGS behavior, and pinned official SDK file formats.
- CI now also validates package separation and produces distinct math and frontend artifacts with SHA-256 checksums.
- **Live Stake staging RGS testing, current publisher requirements, and final security review still require verification.**
- The simulation samples published weighted outcomes; it does **not** represent 104 million independently generated new reel books.

Never merge into `main`, deploy, or submit without explicit owner approval.
