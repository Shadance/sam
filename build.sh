#!/bin/sh -x

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

ARCHITECTURE='x86_64'

VERSION=`cat version`

PYTHON_PATH='python/bin'

cp version src/version
cd src
python setup.py sdist
cd ..

rm -rf build
mkdir build
mkdir build/sam
cd build/sam

wget -O python.tar.gz http://build.syncloud.org:8111/guestAuth/repository/download/thirdparty_python_${ARCHITECTURE}/lastSuccessful/python.tar.gz
tar -xvf python.tar.gz
rm python.tar.gz

wget -O get-pip.py https://bootstrap.pypa.io/get-pip.py
${PYTHON_PATH}/python get-pip.py
rm get-pip.py

${PYTHON_PATH}/pip install ${DIR}/src/dist/syncloud-sam-${VERSION}.tar.gz

cp -r ../../bin bin

cd ..
tar -zcvf sam-${VERSION}-${ARCHITECTURE}.tar.gz sam