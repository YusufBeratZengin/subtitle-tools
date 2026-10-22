# Contributing to subtitle-tools

Thank you for your interest in contributing to `subtitle-tools`. We welcome contributions from the community.

## Design Philosophy

- **Zero runtime dependencies**: The core library and CLI must depend only on the Python standard library. No external packages may be added to `dependencies`.
- **Typing**: The codebase is fully typed (`py.typed`). All new functions, methods, and classes must include type annotations.
- **Robustness**: Parsers must be lenient on malformed input from third-party subtitle editors while writers must emit spec-compliant outputs.
- **Cross-platform**: Code must work identically on Linux, macOS, and Windows.

## Development Workflow

### Prerequisites
- Python >= 3.10
- Git

### Setup
Clone the repository and inspect the codebase:
```bash
git clone https://github.com/YusufBeratZengin/subtitle-tools.git
cd subtitle-tools
```

Optional development dependencies can be installed using `pip`:
```bash
pip install -e ".[dev]"
```

### Running Tests
You can run tests using `pytest`:
```bash
pytest
```

Or using Python's built-in `unittest` runner (requires zero additional packages):
```bash
python -m unittest discover -s tests
```

### Code Style and Conventions
- Follow PEP 8 guidelines.
- Use 4 spaces for indentation.
- Commit messages should follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:
  - `feat: add ASS alignment tag support`
  - `fix: resolve cue overlap calculation edge case`
  - `docs: update Turkish README examples`
  - `test: add malformed WebVTT test case`
- Avoid emojis in commit messages, documentation, and code comments.

## Submitting a Pull Request
1. Fork the repository and create your branch from `main`.
2. Ensure all tests pass.
3. Add tests for any new features or bug fixes.
4. Open a pull request against the `main` branch with a clear description of the change.
