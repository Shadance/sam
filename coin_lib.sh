#!/usr/bin/env bash

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd ${DIR}

if [ ! -d lib ]; then
  mkdir lib
fi

cd lib

coin py https://pypi.python.org/packages/py2/u/urllib3/urllib3-1.10.4-py2-none-any.whl
coin py https://pypi.python.org/packages/source/j/jsonpickle/jsonpickle-0.9.2.tar.gz
coin py https://pypi.python.org/packages/source/c/convertible/convertible-0.13.tar.gz
coin py https://pypi.python.org/packages/source/s/syncloud-app/syncloud-app-0.38.tar.gz

cd ..