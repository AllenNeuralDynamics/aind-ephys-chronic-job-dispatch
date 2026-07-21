# hash:sha256:23df50b2ebac326e96764f672da2cac11b00670d8dff23fc0e5f048ace41b74c
ARG REGISTRY_HOST
FROM $REGISTRY_HOST/codeocean/mambaforge3:24.5.0-0-python3.12.4-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG GIT_ASKPASS
COPY git-ask-pass /

RUN pip install -U --no-cache-dir \
    boto3==1.38.27 \
    s3fs==2025.5.1 \
    spikeinterface[full]==0.102.3

COPY postInstall /
RUN --mount=type=secret,id=secrets . /run/secrets/secrets \
    && /postInstall
