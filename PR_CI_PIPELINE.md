# ci: Add GitHub Actions workflow for automated testing

## Summary

Establishes a comprehensive CI/CD pipeline using GitHub Actions to automate testing, code quality checks, and security scanning. This ensures every commit and PR meets quality standards before merging, providing confidence in code reliability and maintainability.

**Impact**: Automated quality gates for all code changes, visible quality metrics via badges.

---

## What's New

### 1. GitHub Actions CI Workflow (`.github/workflows/ci.yml`)

**Two parallel jobs**:

#### Job 1: Test & Quality Checks
- **PostgreSQL service container** - Runs database for integration tests
- **Alembic migrations** - Ensures schema is up-to-date before tests
- **Test execution** - Full test suite with coverage reporting
- **Coverage upload** - Integrates with Codecov for coverage tracking
- **Linting** - Ruff checks for code style violations
- **Formatting** - Black verifies consistent code formatting
- **Type checking** - Mypy validates type annotations (non-blocking)

#### Job 2: Security Scanning
- **Bandit** - Scans for common security issues in Python code
- **Safety** - Checks dependencies for known vulnerabilities

### 2. README Badges

Added professional badges to README header:
- **CI Status** - Shows if latest build passed/failed
- **Code Coverage** - Displays test coverage percentage
- **License** - MIT license badge (existing)
- **Python Version** - Python 3.11+ requirement (existing)

---

## CI Pipeline Details

### Trigger Conditions

**Runs on**:
- Every push to `main` branch
- Every push to `feat/*` or `fix/*` branches
- Every pull request targeting `main`

### Test Environment

```yaml
services:
  postgres:
    image: postgres:16-alpine
    env:
      POSTGRES_USER: risklens
      POSTGRES_PASSWORD: risklens_dev_password
      POSTGRES_DB: risklens
    ports:
      - 5432:5432
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

**Why this matters**: Tests run against real PostgreSQL, not mocks. Catches database-specific issues.

### Execution Steps

1. **Checkout code** - Clone repository
2. **Setup Python 3.11** - Install Python with pip caching
3. **Install dependencies** - `pip install -e ".[dev]"`
4. **Run migrations** - `alembic upgrade head`
5. **Run tests** - `pytest` with coverage
6. **Upload coverage** - Send to Codecov
7. **Lint** - `ruff check`
8. **Format check** - `black --check`
9. **Type check** - `mypy` (non-blocking)
10. **Security scan** - `bandit` + `safety`

### Expected Runtime

- **Test job**: ~2-3 minutes
- **Security job**: ~1 minute
- **Total**: ~3-4 minutes per run

---

## Quality Standards Enforced

### Must Pass (Blocking)
- ✅ All tests pass
- ✅ Ruff linting passes (no style violations)
- ✅ Black formatting passes (consistent style)

### Advisory (Non-blocking)
- ⚠️ Mypy type checking (reports issues but doesn't fail)
- ⚠️ Bandit security scan (reports issues but doesn't fail)
- ⚠️ Safety vulnerability check (reports issues but doesn't fail)

**Rationale**: Type and security checks are informational during initial setup. Will be made blocking in future PRs after addressing existing issues.

---

## Benefits

### For Development
- **Immediate feedback** - Know if changes break tests within 3 minutes
- **Prevent regressions** - Catch bugs before they reach main branch
- **Consistent quality** - Automated enforcement of code standards
- **Coverage tracking** - See which code paths lack tests

### For Collaboration
- **PR confidence** - Reviewers see green checkmarks before reviewing
- **Merge safety** - Only quality code reaches main branch
- **Documentation** - CI logs show exactly what was tested

### For Interviews
- **Professional impression** - Green badges signal quality
- **Best practices** - Demonstrates CI/CD knowledge
- **Reliability proof** - Tests pass consistently, not just "on my machine"

---

## Verification

### Local Testing (Before Push)

```bash
# Run same checks locally
pytest tests/ -v --cov=src/risklens
ruff check src/ tests/
black --check src/ tests/
mypy src/risklens --ignore-missing-imports
```

### GitHub Actions (After Push)

1. Push branch: `git push origin feat/ci-pipeline`
2. Go to GitHub → Actions tab
3. See workflow running in real-time
4. Wait for green ✅ or investigate red ❌

### Badge Verification

After merge to main:
- README badges will update automatically
- CI badge shows "passing" status
- Coverage badge shows percentage

---

## Configuration Details

### Codecov Integration

**Optional setup** (for coverage badge):
1. Go to https://codecov.io
2. Sign in with GitHub
3. Enable risklens-platform repository
4. Add `CODECOV_TOKEN` to GitHub Secrets (Settings → Secrets)

**Note**: Coverage upload is non-blocking (`continue-on-error: true`). CI passes even without Codecov token.

### Dependency Caching

```yaml
- name: Set up Python 3.11
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    cache: 'pip'  # Caches pip dependencies
```

**Benefit**: Subsequent runs are faster (~30 seconds saved per run).

---

## Future Enhancements

### Phase 2 (Week 2)
- Add Docker image build and push to registry
- Add deployment preview for PRs

### Phase 3 (Week 3)
- Add performance benchmarking
- Add API contract testing

### Phase 4 (Week 4)
- Make mypy blocking (after fixing all type errors)
- Make security scans blocking (after addressing findings)
- Add automated dependency updates (Dependabot)

---

## Technical Decisions

### Why GitHub Actions?
- **Native integration** - Built into GitHub, no external service
- **Free for public repos** - Unlimited minutes
- **Matrix testing** - Easy to test multiple Python versions (future)
- **Marketplace** - Rich ecosystem of pre-built actions

### Why PostgreSQL Service Container?
- **Real database** - Tests against actual PostgreSQL, not SQLite
- **Isolation** - Each CI run gets fresh database
- **Production parity** - Same database engine as production

### Why Non-blocking Security Checks?
- **Gradual adoption** - Don't block development while addressing existing issues
- **Visibility** - Still see security findings in CI logs
- **Future enforcement** - Will be made blocking after cleanup

---

## Breaking Changes

None. This is purely additive - adds CI without changing existing code.

---

## Migration Guide

**For contributors**:
- No action needed
- CI runs automatically on every push
- Fix any issues reported by CI before requesting review

**For maintainers**:
- Optional: Set up Codecov token for coverage badge
- Optional: Configure branch protection rules (require CI to pass before merge)

---

## Checklist

- [x] CI workflow created and tested
- [x] PostgreSQL service container configured
- [x] All test jobs passing
- [x] Badges added to README
- [x] Documentation updated
- [x] Non-blocking checks configured appropriately

---

**Ready to merge!** This PR establishes the foundation for automated quality assurance, ensuring all future code changes meet professional standards.
