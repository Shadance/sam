#!/bin/bash -x

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd ${DIR}

NAME="sam"
ARCHITECTURE=$1
VERSION="local"

if [ ! -z "$2" ]; then
    VERSION=$2
fi

function 3rdparty {
  APP_ID=$1
  APP_FILE=$2
  if [ ! -d ${DIR}/3rdparty ]; then
    mkdir ${DIR}/3rdparty
  fi
  if [ ! -f ${DIR}/3rdparty/${APP_FILE} ]; then
    wget http://build.syncloud.org:8111/guestAuth/repository/download/thirdparty_${APP_ID}_${ARCHITECTURE}/lastSuccessful/${APP_FILE} \
    -O ${DIR}/3rdparty/${APP_FILE} --progress dot:giga
  else
    echo "skipping ${APP_ID}"
  fi
}

pip install --upgrade coin

cd src
python setup.py sdist
cd ..

coin ${DIR}/src/dist/syncloud-sam-${VERSION}.tar.gz --to ${DIR}/lib
./coin_lib.sh

rm -rf build
BUILD_DIR=${DIR}/build/${NAME}
mkdir -p ${BUILD_DIR}

PYTHON_ZIP=python.tar.gz
3rdparty python ${PYTHON_ZIP}

tar -xf ${DIR}/3rdparty/${PYTHON_ZIP} -C ${BUILD_DIR}

cp -r lib ${BUILD_DIR}
cp -r bin ${BUILD_DIR}
cp -r config ${BUILD_DIR}

sed  -i "s/arch:.*/arch: ${ARCHITECTURE}/g" build/${NAME}/config/sam.cfg

mkdir build/${NAME}/META
echo ${NAME} >> build/${NAME}/META/app
echo ${VERSION} >> build/${NAME}/META/version
rm -rf ${NAME}*.tar.gz
tar -zcf ${NAME}-${VERSION}-${ARCHITECTURE}.tar.gz -C build ${NAME}