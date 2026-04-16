# Contributing to DocVault

Thank you for your interest in contributing to DocVault! This guide will help you get started.

## Development Setup

### Prerequisites
- Python 3.12+
- Node.js 20+
- Redis (for Celery and caching)
- PostgreSQL (or SQLite for local dev)

### Backend
```bash
git clone git@github.com:packetloss404/docvault.git
cd docvault
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r docvault/requirements/dev.txt
cp .env.example docvault/.env
cd docvault
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 5000
```

### Frontend
```bash
cd src-ui
npm install
npx ng serve
# Open http://localhost:4200
```

### Docker (all-in-one)
```bash
docker compose up
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

## Code Style

- **Python**: Enforced by [Ruff](https://docs.astral.sh/ruff/) (config in `pyproject.toml`)
- **TypeScript**: Angular CLI defaults

## Running Tests

```bash
# Backend (1,029 tests)
cd docvault && python manage.py test

# Frontend (525 tests)
cd src-ui && npx ng test
```

## Making Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make small, focused changes
4. Write tests for new functionality
5. Ensure all tests pass
6. Commit with a clear message in imperative mood (e.g., "Add document export endpoint")
7. Push and open a pull request

## Where to Find Work

- **Task list**: [`dev/work/CHECKLIST.md`](dev/work/CHECKLIST.md)
- **Repo map**: [`dev/AGENTS.md`](dev/AGENTS.md)
- **Feature specs**: [`dev/work/features/`](dev/work/features/)

## Reporting Issues

- **Bugs**: Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md)
- **Features**: Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md)
- **Security**: See [SECURITY.md](SECURITY.md) — do not open public issues
