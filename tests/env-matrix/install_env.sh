#!/bin/bash

PYVER=$1
DJANGO=$2
ENVNAME=$3

eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

pyenv virtualenv $PYVER $ENVNAME
pyenv shell $ENVNAME
pip install django==$DJANGO pytest pytest-django pytest-asyncio pytest-cov pydantic==1.6
