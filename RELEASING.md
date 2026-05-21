Releasing

This project publishes to PyPI through GitHub Actions using PyPI Trusted Publishing.

## Release flow

1. Make code, test, and documentation changes.
2. Bump the version in:
   - `pyproject.toml`
   - `src/nwtools_mcp/__init__.py`
3. Run the test suite:

```bash
pytest
```

4. Build the distribution artifacts:

```bash
uv build
```

5. Commit and push the release prep to `main`:

```bash
git add .
git commit -m "Prepare X.Y.Z release"
git push origin main
```

6. Create and push the version tag:

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

7. GitHub Actions runs `.github/workflows/publish.yml` and:
   - builds the wheel and sdist
   - smoke-tests both artifacts
   - publishes the release to PyPI

## Versioning rules

- Every PyPI release must use a new version.
- The Git tag should match the package version.
- Example: package version `0.2.1` and tag `v0.2.1`.

Do not reuse an old version number. Publish a new one instead.

## Useful commands

Install from PyPI:

```bash
pip install -U nwtools-mcp
```

Run directly with uv:

```bash
uvx nwtools-mcp
```

Build and publish manually if needed:

```bash
uv build
uv publish
```
