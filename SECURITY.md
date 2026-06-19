# Security and privacy

Do not report real credentials, user memories, conversation logs, or personal
profiles in public issues.

Hermos processes host-provided context and may persist Self Model, memory, or
evidence data when the host explicitly supplies storage paths. Deployments
should:

- keep private runtime data outside the repository;
- restrict filesystem permissions;
- redact tool output before writing evidence logs;
- require approval for Self Model changes;
- treat failed, missing, timed-out, and unknown verification results as not
  passing.

This alpha release has not received an independent security audit.
