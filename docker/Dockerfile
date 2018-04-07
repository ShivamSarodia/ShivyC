FROM ubuntu:artful
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    gcc \
    vim
CMD pip3 install -e . && /bin/bash
