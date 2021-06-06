ARG DOCKER_IMAGE=debian:bullseye-slim
FROM $DOCKER_IMAGE

RUN apt-get update && apt-get -y install \
	make \
    python3 \
    python3-pip \
    gcc \
	git \
#	--no-install-recommends \
	&& apt-get -y autoremove --purge \
	&& rm -rf /var/lib/apt/lists/* \
	&& git clone --recurse-submodules https://github.com/ShivamSarodia/ShivyC.git \
	&& cd ShivyC && python3 setup.py install && python3 -m unittest discover

LABEL author="ShivyC"
LABEL mantainer="ShivyC"

ARG VERSION="1.0.0"
ENV VERSION=$VERSION

#RUN shivyc -h

ENV CC=/usr/bin/shivyc
WORKDIR /usr/src/myapp

CMD ["shivyc", "-h"]

LABEL org.label-schema.schema-version="1.0" \
	  org.label-schema.build-date=$BUILD_DATE \
	  org.label-schema.name="shivyc/shivyc" \
	  org.label-schema.description="build shivyc compiler" \
	  org.label-schema.version=$VERSION \
	  org.label-schema.vendor="shivyc" \
	  org.label-schema.url="shivyc" \
	  org.label-schema.vcs-url="" \
	  org.label-schema.vcs-ref=$VCS_REF \
	  org.label-schema.docker.cmd="docker build -t shivyc/shivyc -f Dockerfile ."
