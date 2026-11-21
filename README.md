# TaskForge

Defensive task management REST API implementing zero-trust tenant boundaries and custom cryptographic primitives.

[![CI](https://github.com/AliSaleh07/TaskForge/actions/workflows/ci.yml/badge.svg)](https://github.com/AliSaleh07/TaskForge/actions/workflows/ci.yml)

## Core Engineering

- **Tenant Isolation**: Tasks are strictly partitioned by authenticated user ID. Cross-tenant access attempts return `404` to avoid leaking resource existence.
- **Cryptographic Security**: PBKDF2-HMAC-SHA256 password hashing (600,000 iterations, 32-byte salt). HMAC-SHA256 JWT validation using constant-time comparison.
- **Defensive HTTP Headers**: Enforces HSTS, CSP, and strict framing policies (`DENY`, `nosniff`).
- **Input Sanitization**: Parameterized SQLite queries and strict Pydantic schemas.

```mermaid
flowchart LR
    Client -->|HTTP / Bearer| MW[Security Headers Middleware]
    MW --> Auth[Auth & JWT Verification]
    Auth --> CRUD[Task Service]
    CRUD --> DB[(SQLite Database)]
```

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn taskforge.main:app --reload
```

## Running Tests

```bash
pytest -v tests/
```

## Endpoints

- `POST /api/v1/auth/register` - Create account (enforces complexity rules)
- `POST /api/v1/auth/login` - Obtain signed JWT
- `GET /api/v1/auth/me` - Profile lookup
- `GET /api/v1/tasks` - List tasks (supports `status`, `priority`, `search`, pagination)
- `POST /api/v1/tasks` - Create task
- `GET /api/v1/tasks/{id}` - Fetch single task
- `PUT /api/v1/tasks/{id}` - Update task details
- `DELETE /api/v1/tasks/{id}` - Delete task
- `GET /api/v1/tasks/stats/summary` - Aggregate metrics
