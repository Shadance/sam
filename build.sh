#!/bin/bash -x

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd ${DIR}
NAME="sam"

ARCH=$(dpkg-architecture -qDEB_HOST_GNU_CPU)
if [ ! -z "$1" ]; then
    ARCH=$1
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

DOWNLOAD_URL=http://build.syncloud.org:8111/guestAuth/repository/download
coin --to ${BUILD_DIR} raw ${DOWNLOAD_URL}/thirdparty_python_${ARCH}/lastSuccessful/python-${ARCH}.tar.gz

cp -r lib ${BUILD_DIR}
cp -r bin ${BUILD_DIR}
cp -r config ${BUILD_DIR}

sed  -i "s/arch:.*/arch: ${ARCH}/g" build/${NAME}/config/sam.cfg

mkdir build/${NAME}/META
echo ${NAME} >> build/${NAME}/META/app
echo ${VERSION} >> build/${NAME}/META/version
rm -rf ${NAME}*.tar.gz
tar -zcf ${NAME}-${VERSION}-${ARCH}.tar.gz -C build ${NAME}