#!/bin/bash -x

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd ${DIR}
NAME="sam"

ARCHITECTURE=$(dpkg-architecture -qDEB_HOST_GNU_CPU)
if [ ! -z "$1" ]; then
    ARCHITECTURE=$1
fi

VERSION="local"
if [ ! -z "$2" ]; then
    VERSION=$2
fi

pip install --upgrade coin

rm -f src/version
echo ${VERSION} >> src/version

cd src
python setup.py sdist
cd ..

./coin_lib.sh
coin  --to ${DIR}/lib py ${DIR}/src/dist/syncloud-sam-${VERSION}.tar.gz

rm -rf build
BUILD_DIR=${DIR}/build/${NAME}
mkdir -p ${BUILD_DIR}

PYTHON_ZIP=python.tar.gz
coin --to ${BUILD_DIR} --cache_folder python_${ARCHITECTURE} raw http://build.syncloud.org:8111/guestAuth/repository/download/thirdparty_python_${ARCHITECTURE}/lastSuccessful/${PYTHON_ZIP}

cp -r lib ${BUILD_DIR}
cp -r bin ${BUILD_DIR}
cp -r config ${BUILD_DIR}

sed  -i "s/arch:.*/arch: ${ARCHITECTURE}/g" build/${NAME}/config/sam.cfg

mkdir build/${NAME}/META
echo ${NAME} >> build/${NAME}/META/app
echo ${VERSION} >> build/${NAME}/META/version
rm -rf ${NAME}*.tar.gz
tar -zcf ${NAME}-${VERSION}-${ARCHITECTURE}.tar.gz -C build ${NAME}