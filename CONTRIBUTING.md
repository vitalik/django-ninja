# Contributing

Django Ninja uses [uv](https://docs.astral.sh/uv/) to manage the development environment, build, package and publish the project.

To install it follow the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/), or use:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Once you have it - to install all dependencies required for development and testing use this command:


```
uv sync
```

This creates a `.venv` virtual environment with Django Ninja installed in editable mode along with all development dependencies.

Dependency versions are pinned in the committed `uv.lock` file. If you change dependencies in `pyproject.toml`, running `uv sync` (or `uv lock`) updates `uv.lock` automatically — commit the updated lockfile together with your change, as CI validates it with `uv sync --locked`.

Once done you can check if all works with 

```
uv run pytest
```

or using Makefile:

```
make test
```

Now you are ready to make your contribution


When you're done please make sure you to test your functionality 
and check the coverage of your contribution.

```
uv run pytest --cov=ninja --cov-report term-missing tests
```

or using Makefile:

```
make test-cov
```
 
## Code style

Django Ninja uses `ruff`, and `mypy` for style checks.

Run `uv run pre-commit install` to create a git hook to fix your styles before you commit.

Alternatively, manually check your code with:

```
uv run ruff format --check ninja tests
uv run ruff check ninja tests
uv run mypy ninja
```

or using Makefile:

```
make lint
```

Or reformat your code with:

```
uv run ruff format ninja tests
uv run ruff check ninja tests --fix
```

or using Makefile:

```
make fmt
```
 
## Docs
Please do not forget to document your contribution

Django Ninja uses `mkdocs`:

```
cd docs/
uv run --with-requirements requirements.txt mkdocs serve
```

or using Makefile:

```
make docs
```

and go to browser to see changes in real time
