# Local Development Setup

This document expands the brief README setup section with troubleshooting and platform-specific notes.

## Python version requirement: 3.10-3.13

The project pins `torch==2.5.1` (deep learning runtime for YOLO inference). PyTorch 2.5.1 ships wheels for Python 3.10-3.13 only.

**System checks:**

```bash
python --version
# Acceptable: 3.10.x, 3.11.x, 3.12.x, 3.13.x
# Not acceptable: 3.9.x or 3.14.x+
```

## Option 1: pyenv (recommended)

Install pyenv: https://github.com/pyenv/pyenv#installation

Then:

```bash
pyenv install 3.11
cd /path/to/Drone-GeoAnalysis-LLMs
pyenv local 3.11   # creates .python-version
python --version   # 3.11.x
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

The `.python-version` file at the repo root already pins `3.11`, so `pyenv local` is set automatically once you have 3.11 installed.

## Option 2: Docker (no local Python needed)

```bash
cp .env.example .env
# Edit .env with your API keys
docker-compose up --build
```

Tests inside the container:

```bash
docker-compose run --rm drone-geo-app pytest tests/ --cov=src
```

## Option 3: System Python (if version is in range)

```bash
python3.11 -m venv .venv  # use specific version
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
pytest
```

## Troubleshooting

### `ERROR: Could not find a version that satisfies the requirement torch==2.5.1`

Your Python is outside 3.10-3.13. Install a compatible version (see Option 1).

### `ModuleNotFoundError: No module named 'openai'`

Dev dependencies not installed. Run:

```bash
pip install -r requirements-dev.txt
```

(`requirements-dev.txt` includes `-r requirements.txt`, so it installs everything.)

### `pytest: command not found`

Activate the venv first: `source .venv/bin/activate`. If still missing:

```bash
pip install pytest pytest-cov pytest-xdist pytest-timeout
```

### Coverage gate fails with `--cov-fail-under=55`

Run only the test selection you care about (e.g. `pytest tests/services_test/`) with `--no-cov` to disable the gate locally for development:

```bash
pytest tests/services_test/ -o addopts="--no-cov --tb=short"
```

The coverage gate is enforced in CI; local exemption is acceptable during development.

### `parrot-olympe` install fails

Parrot Olympe 7.7.5 requires Linux and Python 3.8-3.11. On Python 3.12+ or macOS, it will fail. This is expected — the drone SDK is optional for local development. Tests use simulation mode automatically when Olympe is not importable. See `docs/INSTALACION_PARROT_OLYMPE.md` for full Olympe setup instructions.

## CI environment (reference)

GitHub Actions uses Python 3.11 (see `.github/workflows/ci.yml`). To exactly match CI locally, use 3.11.

## ADR reference

See [ADR-001](adr/ADR-001-coverage-incremental.md) for coverage gate policy.
