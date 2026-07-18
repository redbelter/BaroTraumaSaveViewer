name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    name: Run tests (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install --upgrade pip setuptools wheel
          pip install pytest pyside6>=6.6.0

      - name: Run pytest
        env:
          PYTHONPATH: src
        run: |
          python -m pytest tests/ -v --tb=short

  lint:
    name: Lint and type check
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install linting tools
        run: |
          pip install --upgrade pip
          pip install ruff mypy

      - name: Run Ruff linter
        run: |
          ruff check src/ tests/

      - name: Run MyPy type checker
        run: |
          mypy src/

  build:
    name: Build PyInstaller artifacts
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install PyInstaller and dependencies
        run: |
          pip install --upgrade pip setuptools wheel
          pip install pyside6>=6.6.0 pyinstaller

      - name: Build executable (Windows)
        if: matrix.os == 'windows-latest'
        run: |
          python -m PyInstaller --clean -y reverse-baro.spec

      - name: Build executable (Linux/macOS)
        if: matrix.os != 'windows-latest'
        run: |
          python -m PyInstaller --clean -y reverse-baro.spec
          ls -lh dist/

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: reverse-baro-${{ matrix.os }}
          path: dist/reverse-baro/
