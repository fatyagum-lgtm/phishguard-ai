# Release scope

This directory continues the original PhishGuard checkpoint; it is a new independent
implementation inspired by the stated hackathon concept. The initial installation
approval blocker was resolved by explicit user authorization. Python dependencies
were installed in isolated virtual environments and Node dependencies locally.

Implemented: data acquisition, real-data training, domain-disjoint evaluation,
calibration, feature ablations, perturbations, FastAPI, React, tests and documentation.
See `reports/validation/summary.json` and `docs/validation.md` for executed checks.
A configured workflow is not evidence of a hosted CI pass. No publication occurred.
External/temporal validation and a trained email model remain future research.
