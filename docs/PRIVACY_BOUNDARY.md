# Privacy boundary

## Public repository

- Generic architecture and interfaces.
- Synthetic domain and alias examples.
- Deterministic tests and fixtures.
- Evaluation methods and sanitized evidence schemas.

## Private host data

- User profiles and relationship data.
- Real project aliases and business vocabulary.
- Conversation history and long-term memories.
- Tool outputs containing private paths or content.
- API keys, tokens, cookies, and authorization codes.
- Production evidence logs.

Private configuration should be loaded at runtime from ignored files or a
secrets/configuration service. The library ships with generic defaults only.
