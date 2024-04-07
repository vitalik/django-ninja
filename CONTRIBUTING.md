# Contributing

Django Ninja uses Flit to build, package and publish the project.

to install it use:

```
pip install flit
```

Once you have it - to install all dependencies required for development and testing  use this command:


```
flit install --deps develop --symlink
```

Once done you can check if all works with 

```
pytest .
```

or using Makefile:

```
make test
```

Now you are ready to make your contribution


When you're done please make sure you to test your functionality 
and check the coverage of your contribution.

```
pytest --cov=ninja --cov-report term-missing tests
```

or using Makefile:

```
make test-cov
```
 
## Code style

Django Ninja uses `ruff`, and `mypy` for style checks.

Run `pre-commit install` to create a git hook to fix your styles before you commit.

Alternatively, manually check your code with:

```
ruff format --check ninja tests
ruff check ninja tests
mypy ninja
```

or using Makefile:

```
make lint
```

Or reformat your code with:

```
ruff format ninja tests
ruff check ninja tests --fix
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
mkdocs serve
```
and go to browser to see changes in real time

