#!/usr/bin/env bash
set -x
set -e

pip install mkdocs==1.1.2 mkdocs-material==5.1.7 markdown-include==0.5.1 jinja2==3.0.3

cd docs
mkdocs build

