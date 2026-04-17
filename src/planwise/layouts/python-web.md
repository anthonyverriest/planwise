<layout>

```
src/<pkg>/
├── main.py                         # App entry point
├── api/                            # HTTP layer
│   ├── __init__.py
│   ├── deps.py                     # Dependency-injection providers for handlers
│   ├── errors.py                   # Exception handlers (domain errors → HTTP responses)
│   └── v1/
│       ├── __init__.py             # Registers all v1 routers under /v1
│       ├── health.py               # Health / readiness endpoints
│       └── <resource>/
│           ├── __init__.py
│           ├── router.py           # Endpoint handlers for this resource
│           └── schemas.py          # Request / response schemas
├── domain/                         # Business logic
│   ├── __init__.py
│   └── <aggregate>/
│       ├── __init__.py
│       ├── models.py               # Entities and value objects
│       ├── service.py              # Use cases / application services
│       ├── repository.py           # Repository interface
│       └── errors.py               # Domain exceptions
├── adapters/                       # External-system integrations
│   ├── __init__.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py              # Database session factory
│   │   ├── models.py               # Persistence models / table mappings
│   │   └── repositories.py         # Repository implementations
│   ├── http/                       # Outbound HTTP clients
│   └── cache/                      # Cache adapters
├── core/                           # Cross-cutting infrastructure
│   ├── __init__.py
│   ├── config.py                   # Settings / configuration
│   ├── logging.py                  # Logging setup
│   └── security.py                 # Auth primitives
└── py.typed                        # PEP 561 marker

alembic/                            # Database migrations
├── env.py
├── script.py.mako
└── versions/
alembic.ini                         # Migration tool configuration

tests/                              # Mirrors src/<pkg>/
├── unit/                           # Tests with no external dependencies
│   └── domain/
├── integration/                    # Tests against real external systems
│   ├── adapters/
│   └── api/
└── conftest.py                     # Shared test fixtures
```

</layout>
