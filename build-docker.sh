#! /usr/bin/env bash
set -e

rm -rf ./docker/source || true
mkdir ./docker/source
cp -rf ./brewblox_ctl_lib/* ./docker/source/

# recursively clean all pycache/pyc files
find ./docker/source/ | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf

docker build --no-cache -t brewblox/brewblox-ctl-lib:local docker
