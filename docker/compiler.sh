#!/bin/bash
#//////////////////////////////////////////////////////////////
#//                                                          //
#//  Script, 2021                                            //
#//  Created: 27, May, 2021                                  //
#//  Modified: 27, May, 2021                                 //
#//  file: -                                                 //
#//  -                                                       //
#//  Source: https://github.com/bensuperpc/docker-ShivyC     //
#//  OS: ALL                                                 //
#//  CPU: ALL                                                //
#//                                                          //
#//////////////////////////////////////////////////////////////

TAG_VERSION=latest
DOCKER_IMAGE=shivyc/shivyc
COMPILER_EXEC=shivyc

case "$1" in
    -version|-v)
        TAG_VERSION=$2
        shift
        shift
        ;;&
    -h)
        echo "Usage: ${0##*/} [-version latest $COMPILER_EXEC hello.c]"
        exit 1
        ;;
esac

if [ $# -eq 0 ]
then
    echo "No arguments supplied"
    exit 1
fi

docker run --rm -v "$PWD":/usr/src/myapp -w /usr/src/myapp ${DOCKER_IMAGE}:${TAG_VERSION} $@
