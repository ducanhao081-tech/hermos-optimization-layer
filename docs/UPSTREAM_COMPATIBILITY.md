# Upstream compatibility

Hermos is an independent project inspired by integration work around
NousResearch/Hermes-Agent. It is not affiliated with or endorsed by
NousResearch.

The extracted package currently avoids importing Hermes Agent internals. A
future adapter should target the latest upstream release and keep all
framework-specific code in a separate adapter module.

Compatibility claims must include:

- the exact Hermes Agent commit or release;
- the Hermos version;
- the supported Python version;
- the integration tests executed;
- any disabled upstream features or known conflicts.
