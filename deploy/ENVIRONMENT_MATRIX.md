# Environment Matrix

## Backend Secrets And Runtime

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | Yes | FastAPI and SQLAlchemy PostgreSQL connection |
| `REDIS_URL` | Yes | Redis connection for cache and rate-limit/session behavior |
| `SECRET_KEY` | Yes | JWT and application security secret |
| `CORS_ORIGINS` | Yes | Explicit list of allowed frontend origins for credentialed browser requests |
| `MODEL_PROVIDER` | Yes | Active LLM provider |
| `DEFAULT_MODEL` | Yes | Default tutoring/application model |
| `FAST_MODEL` | Recommended | Lower-latency model for cheaper paths |
| `OPENAI_API_KEY` | If using OpenAI | LLM access |
| `ANTHROPIC_API_KEY` | If using Anthropic | LLM access |
| `GEMINI_API_KEY` | If using Gemini | LLM access |
| `DB_POOL_SIZE` | Recommended | SQLAlchemy connection pool sizing |
| `DB_MAX_OVERFLOW` | Recommended | SQLAlchemy overflow pool sizing |
| `LOG_LEVEL` | Recommended | Logging verbosity |
| `DEBUG` | Yes | Must be `false` in production |

## Frontend Build And Runtime

| Variable | Required | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | Yes | Public API base URL baked into frontend build |
| `NODE_ENV` | Yes | Must be `production` |
| `API_INTERNAL_URL` | Optional | Internal backend URL during image build or server-side calls |

## Infrastructure

| Variable | Required | Purpose |
| --- | --- | --- |
| `POSTGRES_DB` | If self-hosted DB | Database name |
| `POSTGRES_USER` | If self-hosted DB | Database user |
| `POSTGRES_PASSWORD` | If self-hosted DB | Database password |
| `REDIS_PASSWORD` | If self-hosted Redis | Redis password |
| `BACKEND_PORT` | Optional | Host bind port if directly mapped |
| `FRONTEND_PORT` | Optional | Host bind port if directly mapped |

## Important Notes

- `NEXT_PUBLIC_API_URL` is a frontend public variable and must point to the real production API hostname.
- `CORS_ORIGINS` should be a JSON array or comma-separated string accepted by `src/config.py`.
- Do not leave production secrets only in a manually edited `.env` on a developer machine.
- Keep production values separate from local development values.
- If frontend and backend are deployed from images, rebuild frontend whenever `NEXT_PUBLIC_API_URL` changes.
