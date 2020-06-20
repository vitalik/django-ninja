#!/usr/bin/env bash
set -x
set -e
# Install pip
cd /tmp
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3.6 get-pip.py --user
cd -

# Install deps
python3.6 -m pip install --user -r requirements.dev.txt

# build docs
cd docs
python3.6 -m mkdocs build
