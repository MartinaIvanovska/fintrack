# Backend tests

## Setup

```bash
./scripts/setup-venv.sh            # from the repo root: backend/.venv (Python 3.12), test tools, Chromium
source backend/.venv/bin/activate
cd backend
```

No local Python? `docker compose --profile test run --rm backend-tests [pytest args]` runs the same suite.

## Layout

| Folder | Tier | Needs | Default run |
|---|---|---|---|
| `unit/` | pure logic, database mocked | nothing | yes |
| `property/` | Hypothesis properties | nothing | yes |
| `integration/` | real app + real MongoDB | Docker (Testcontainers) or `MONGO_URI` | yes |
| `api/` | Schemathesis fuzzing over real HTTP | Docker or `MONGO_URI` | `pytest tests/api` |
| `e2e/` | Playwright + axe against the running stack | `docker compose up -d` | `pytest tests/e2e` |
| `support/` | shared helpers: data factory, production index list | — | — |

## Common commands

```bash
pytest                                  # unit + property + integration
pytest --cov                            # ... with the 100 % coverage gate
pytest tests/unit -k budget -v          # a subset
pytest --hypothesis-profile=ci          # more property examples, derandomized
pytest -rxX                             # list expected failures with reasons
pytest --runxfail -k <name>             # see why an expected failure fails
MONGO_URI=mongodb://localhost:27017 pytest tests/integration   # reuse a running MongoDB
mutmut run && mutmut results            # mutation testing (business logic)
```

