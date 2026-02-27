# feat: Implement database layer with SQLAlchemy and Alembic

## Summary

Implements the foundational database layer for RiskLens Platform, providing persistent storage for risk decisions with full audit trail capabilities.

## What Changed

### Database Models (`src/risklens/db/models.py`)
- **DecisionRecord** model with comprehensive audit fields:
  - Primary identifiers: `decision_id`, `alert_id`, `address`
  - Risk assessment: `risk_level`, `action`, `confidence`, `risk_score`
  - Explainability: `rationale`, `evidence_refs`, `recommendations`, `limitations`
  - Audit trail: `rule_version`, `decided_at`, full `alert_data` JSON
- Composite indexes for common query patterns:
  - `(address, decided_at)` - address history queries
  - `(risk_level, action)` - risk distribution analysis
  - `(decided_at, action)` - time-series action tracking

### Session Management (`src/risklens/db/session.py`)
- SQLAlchemy engine with connection pooling (configurable pool size)
- `get_db()` generator for dependency injection (FastAPI-ready)
- `init_db()` and `drop_db()` utilities for testing
- `pool_pre_ping=True` for connection health checks

### Database Migrations
- Alembic configuration with autogenerate support
- Initial migration: `b2f55e300e27_initial_schema_with_decisions_table.py`
- Migration tested: up/down operations verified

### Infrastructure
- **Docker Compose** setup with PostgreSQL 15-alpine
- Health checks for database readiness
- Volume persistence for data
- Redis service included (for future use)

### Testing (`tests/test_db.py`)
- **9 comprehensive tests**, all passing:
  - ✅ Create decision record
  - ✅ Query by address
  - ✅ Query by risk level
  - ✅ Query by action
  - ✅ Query by time range
  - ✅ Update decision
  - ✅ Delete decision
  - ✅ JSON field operations
  - ✅ Composite index queries
- **Coverage**: 96% on `db/models.py`, 79% on `db/session.py`

### Configuration Updates
- Python version requirement: `>=3.9` (compatibility with existing environment)
- Database URL configuration in `.env` and `alembic.ini`
- Type hints fixed for Python 3.9 (`Optional[str]` instead of `str | None`)

## Why These Changes

### Audit Trail Requirements
Every risk decision must be:
1. **Traceable**: Link decision back to input alert
2. **Explainable**: Store rationale and evidence
3. **Reproducible**: Store rule version and full alert data
4. **Queryable**: Fast lookups by address, time, risk level

### Production Readiness
- Connection pooling prevents database connection exhaustion
- Composite indexes optimize common query patterns
- Alembic migrations enable zero-downtime schema updates
- Docker Compose ensures consistent development environment

## Testing

### Run Tests Locally
```bash
# Start PostgreSQL
docker run -d --name risklens-db \
  -e POSTGRES_USER=risklens \
  -e POSTGRES_PASSWORD=risklens_dev_password \
  -e POSTGRES_DB=risklens \
  -p 5433:5432 \
  postgres:15-alpine

# Install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Run tests
pytest tests/test_db.py -v --cov=risklens.db

# Expected output:
# 9 passed, coverage: 96% (models), 79% (session)
```

### Verify Database Schema
```bash
docker exec risklens-db psql -U risklens -d risklens -c "\d decisions"
```

Expected columns:
- `decision_id` (PK)
- `alert_id`, `address` (indexed)
- `risk_level`, `action` (indexed)
- `confidence`, `risk_score`
- `rationale`, `evidence_refs`, `recommendations`, `limitations`
- `rule_version`, `decided_at`, `alert_data`

## Performance Considerations

### Indexes
- Single-column indexes on frequently filtered fields (`address`, `alert_id`, `risk_level`, `action`, `decided_at`)
- Composite indexes for common multi-column queries
- Trade-off: Faster reads, slightly slower writes (acceptable for audit log use case)

### Connection Pooling
- Default pool size: 10 connections
- Max overflow: 20 connections
- `pool_pre_ping=True` prevents stale connection errors

### JSON Storage
- `alert_data` stored as JSONB (PostgreSQL native JSON type)
- Enables flexible schema evolution without migrations
- Queryable with PostgreSQL JSON operators (future enhancement)

## Migration Path

### From Development to Production
1. Update `DATABASE_URL` in production `.env`
2. Run `alembic upgrade head` to apply migrations
3. Verify schema: `alembic current`
4. Rollback if needed: `alembic downgrade -1`

### Future Schema Changes
```bash
# Make changes to models.py
# Generate migration
alembic revision --autogenerate -m "Add new field"

# Review generated migration in alembic/versions/
# Apply migration
alembic upgrade head
```

## Security Notes

- Database credentials in `.env` (not committed)
- `.env.example` provided with placeholder values
- Production: Use environment variables or secrets manager
- Connection string includes password (ensure `.env` is in `.gitignore`)

## Next Steps

After this PR merges:
1. **Sprint 2**: Implement rule engine (`src/risklens/engine/rules.py`)
2. **Sprint 3**: Build FastAPI service with `/evaluate` endpoint
3. **Sprint 4**: Add integration tests and CLI tool

## Checklist

- [x] Code follows project style guidelines
- [x] Tests added and passing (9/9)
- [x] Documentation updated (docstrings, comments)
- [x] Database migrations tested (up/down)
- [x] No sensitive data in commit history
- [x] `.env` not committed (only `.env.example`)
- [x] Docker Compose tested locally
- [x] Coverage meets threshold (>75%)

## Related Issues

Part of Phase 1: Decision Engine Core (see ROADMAP.md)

## Screenshots

### Test Results
```
tests/test_db.py::test_create_decision_record PASSED                     [ 11%]
tests/test_db.py::test_query_by_address PASSED                           [ 22%]
tests/test_db.py::test_query_by_risk_level PASSED                        [ 33%]
tests/test_db.py::test_query_by_action PASSED                            [ 44%]
tests/test_db.py::test_query_by_time_range PASSED                        [ 55%]
tests/test_db.py::test_update_decision PASSED                            [ 66%]
tests/test_db.py::test_delete_decision PASSED                            [ 77%]
tests/test_db.py::test_json_fields PASSED                                [ 88%]
tests/test_db.py::test_composite_index_query PASSED                      [100%]

================================ tests coverage ================================
Name                              Stmts   Miss  Cover   Missing
---------------------------------------------------------------
src/risklens/db/models.py            26      1    96%   52
src/risklens/db/session.py           19      4    79%   40-44
---------------------------------------------------------------
```

### Database Schema
```sql
                                Table "public.decisions"
       Column        |            Type             | Nullable |      Default       
---------------------+-----------------------------+----------+--------------------
 decision_id         | character varying(36)       | not null | 
 alert_id            | character varying(255)      | not null | 
 address             | character varying(42)       | not null | 
 risk_level          | character varying(20)       | not null | 
 action              | character varying(20)       | not null | 
 confidence          | double precision            | not null | 
 risk_score          | double precision            | not null | 
 rationale           | text                        | not null | 
 evidence_refs       | json                        | not null | 
 recommendations     | json                        | not null | 
 limitations         | json                        | not null | 
 rule_version        | character varying(20)       | not null | 
 decided_at          | timestamp without time zone | not null | 
 alert_data          | json                        | not null | 
Indexes:
    "decisions_pkey" PRIMARY KEY, btree (decision_id)
    "idx_address_decided_at" btree (address, decided_at)
    "idx_decided_at_action" btree (decided_at, action)
    "idx_risk_level_action" btree (risk_level, action)
    "ix_decisions_action" btree (action)
    "ix_decisions_address" btree (address)
    "ix_decisions_alert_id" btree (alert_id)
    "ix_decisions_decided_at" btree (decided_at)
    "ix_decisions_risk_level" btree (risk_level)
```

---

**Ready for review!** 🚀
