#!/usr/bin/env bash
set -x
set -e

pip install docs/requirements.txt

cd docs
mkdocs build
