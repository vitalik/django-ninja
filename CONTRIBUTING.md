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


When you done:

Please make sure you made tests to cover your functionality 

and finally check the resulting coverage of your contribution did not suffer

```
pytest --cov=ninja --cov-report term-missing tests
```

or using Makefile:

```
make test-cov
```
 
## Code style

Django Ninja uses `black`, `isort` and `flake8` for style check

Before your commit please check your code with:

```
black --check ninja
isort --check ninja
flake8 ninja
```

or using Makefile:

```
make lint
```

Or reformat your code with:

```
black ninja
isort ninja
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

