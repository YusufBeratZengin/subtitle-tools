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

The `transcribe`, `ffmpeg`, and `yaml` extras are only needed to run
`subtool transcribe` against real media. The test suite mocks faster-whisper and
ffmpeg, blocks network access, and never downloads a model; keep it that way and use
only invented phrases in transcription tests. faster-whisper must stay a lazy import
so that the core package keeps zero runtime dependencies.

Enable the local credential guard once per clone:
```bash
git config core.hooksPath .githooks
```

The pre-commit hook scans staged files for common credential patterns and prints
paths only, never the matching content. It is a baseline guard: review the staged
diff for personal data and credentials too, and do not bypass a failed hook.

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

## Releasing

Before the first release, configure a PyPI pending publisher for
`YusufBeratZengin/subtitle-tools`, workflow `publish.yml`, and environment `pypi`.
Create the matching GitHub Actions environment. Publishing uses OIDC trusted
publishing; no PyPI API token is stored in the repository or GitHub secrets.

1. Update `CHANGELOG.md` and bump the version in `pyproject.toml` using SemVer.
2. Run the checks and validate the distributions locally:

   ```bash
   ruff check .
   mypy src
   pytest
   python -m build
   twine check dist/*
   ```

3. Commit the release as `chore(release): vX.Y.Z`.
4. Create the matching tag with `git tag vX.Y.Z` and push the release commit and tag
   when authorized. The tag must match the version in `pyproject.toml`.
5. The `Publish` workflow builds the distributions, transfers the `dist` artifact,
   and publishes it to PyPI from the `pypi` environment. Confirm the resulting PyPI
   release and update the README installation note after the first release.
