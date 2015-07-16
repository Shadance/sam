#!/bin/bash -x

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd ${DIR}

NAME="sam"
ARCHITECTURE=$1
VERSION="local"

if [ ! -z "$2" ]; then
    VERSION=$2
fi

rm -f src/version
echo ${VERSION} >> src/version
cd src
python setup.py sdist
cd ..

rm -rf build
mkdir build
mkdir build/${NAME}
cd build/${NAME}

wget -O python.tar.gz http://build.syncloud.org:8111/guestAuth/repository/download/thirdparty_python_${ARCHITECTURE}/lastSuccessful/python.tar.gz  --progress dot:giga
tar -xf python.tar.gz
rm python.tar.gz

PYTHON_PATH='python/bin'

wget -O get-pip.py https://bootstrap.pypa.io/get-pip.py
${PYTHON_PATH}/python get-pip.py
rm get-pip.py

${PYTHON_PATH}/pip install ${DIR}/src/dist/syncloud-sam-${VERSION}.tar.gz

cd ../..

cp -r bin build/${NAME}
cp -r config build/${NAME}

mkdir build/${NAME}/META
echo ${NAME} >> build/${NAME}/META/app
echo ${VERSION} >> build/${NAME}/META/version

tar -zcf ${NAME}-${VERSION}-${ARCHITECTURE}.tar.gz -C build ${NAME}