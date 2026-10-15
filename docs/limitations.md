# Limitations and non-goals

- Single-source, fixed-seed, 40,000-row subset. No external, campaign-level or
  temporal evaluation and no independent label verification. Domain grouping
  cannot eliminate formatting artifacts shared across domains.
- Every legitimate training example has HTTPS and www. Absence of those patterns
  can produce high scores on harmless inputs. Calibration transfers only under
  compatible distributions; low ECE does not establish reliable deployment risk.
- Canonicalization is an explicit RFC-oriented contract, not a complete browser
  WHATWG URL implementation. Ambiguous numeric authority forms are rejected.
  Public-suffix data is bundled and version-pinned, so later suffix changes are absent.
- The review band/range checks are heuristics and do not detect all distribution
  shifts. A review result does not make a score reliable; a likely-legitimate result
  does not certify a URL. No browsing, DNS, reputation or page-content analysis occurs.
- Email rules are primarily English keywords, not semantic intent detection.
  Negation and benign security advice can trigger them. Headers can be forged.
  MIME defects, truncated content and unsupported links are disclosed; attachments
  are not scanned, decoded or decompressed. There is no trained email classifier.
- Controlled perturbations measure sensitivity. Some change destination/meaning;
  no real-world evasion or preserved-ground-truth claim is made. No links were visited.
- Bootstrap intervals omit training and source uncertainty. Forest ranking metrics
  showed small run-to-run differences; portable serving equivalence was checked.
- Linux Python 3.12 / Node 24 was validated. No macOS/Windows, hosted CI, Docker,
  concurrency load test, formal security audit or production SLA is claimed.
- This is neither a certified forensic tool nor a chain-of-custody system.

The roadmap is targeted at these gaps: independent timestamped datasets, multiple
seeds, campaign-aware partitions, bias mitigation, cost-sensitive operating points
and separately evaluated email models. They are not implemented features.
