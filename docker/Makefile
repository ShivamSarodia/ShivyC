#//////////////////////////////////////////////////////////////
#//                                                          //
#//  Script, 2021                                            //
#//  Created: 06, June, 2021                                 //
#//  Modified: 06, June, 2021                                //
#//  file: -                                                 //
#//  -                                                       //
#//  Source: https://github.com/ShivamSarodia/ShivyC         //
#//          https://github.com/bensuperpc/docker-ShivyC     //
#//  OS: ALL                                                 //
#//  CPU: ALL                                                //
#//                                                          //
#//////////////////////////////////////////////////////////////
BASE_IMAGE := debian:bullseye-slim
IMAGE_NAME := shivyc/shivyc
DOCKERFILE := Dockerfile

DOCKER := docker

TAG := $(shell date '+%Y%m%d')-$(shell git rev-parse --short HEAD)
DATE_FULL := $(shell date -u "+%Y-%m-%dT%H:%M:%SZ")
UUID := $(shell cat /proc/sys/kernel/random/uuid)
VERSION := 1.0.0

#Disable linux/386 linux/arm64 linux/ppc64le linux/s390x linux/arm/v7 linux/arm/v6
ARCH_LIST := linux/amd64
comma:= ,
COM_ARCH_LIST:= $(subst $() $(),$(comma),$(ARCH_LIST))

$(ARCH_LIST): $(DOCKERFILE)
	$(DOCKER) buildx build . -f $(DOCKERFILE) -t $(IMAGE_NAME):$(TAG) -t $(IMAGE_NAME):latest \
	--build-arg BUILD_DATE=$(DATE_FULL) --build-arg DOCKER_IMAGE=$(BASE_IMAGE) --platform $@ \
	--build-arg VERSION=$(VERSION) --load

	
all: $(DOCKERFILE)
	$(DOCKER) buildx build . -f $(DOCKERFILE) -t $(IMAGE_NAME):$(TAG) -t $(IMAGE_NAME):latest \
	--build-arg BUILD_DATE=$(DATE_FULL) --build-arg DOCKER_IMAGE=$(BASE_IMAGE) --platform $(COM_ARCH_LIST) \
	--build-arg VERSION=$(VERSION) --push

push: all

# https://github.com/linuxkit/linuxkit/tree/master/pkg/binfmt
qemu:
	export DOCKER_CLI_EXPERIMENTAL=enabled
	$(DOCKER) run --rm --privileged multiarch/qemu-user-static --reset -p yes
	$(DOCKER) buildx create --name qemu_builder --driver docker-container --use
	$(DOCKER) buildx inspect --bootstrap

clean:
	$(DOCKER) images --filter='reference=$(IMAGE_NAME)' --format='{{.Repository}}:{{.Tag}}' | xargs -r $(DOCKER) rmi -f

.PHONY: build push clean qemu $(ARCH_LIST)
