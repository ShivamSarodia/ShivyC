FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    python3 \
    python3-venv \
    gcc \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment
RUN python3 -m venv /opt/venv

# Make sure we use the virtualenv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /ShivyC

# Activate venv by default in bash
RUN echo "source /opt/venv/bin/activate" >> /root/.bashrc

CMD ["sh", "-c", "pip install -e . && /bin/bash"]
