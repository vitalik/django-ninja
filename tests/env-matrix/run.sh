#!/bin/bash

ENVNAME=$1

eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

echo $ENVNAME

pyenv shell $ENVNAME
pytest tests
