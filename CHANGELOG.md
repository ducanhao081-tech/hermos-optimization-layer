# Changelog

## 0.3.2-alpha - 2026-06-19

- Extracted Self Model, typed memory, context filter, query analyzer, and
  runtime closed-loop modules into a standalone package.
- Removed embedded personal data, private project aliases, logs, and local
  paths.
- Changed query and domain routing to host-supplied configuration.
- Fixed completion gating so failed verification cannot authorize completion.
- Disabled implicit evidence writes; the host must provide an explicit path.
