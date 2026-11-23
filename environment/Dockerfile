# hash:sha256:4678eba7eb83ceba0b9c2f08d78921311347260c4aff5bb914b2f64f544dbf69
ARG REGISTRY_HOST
FROM $REGISTRY_HOST/codeocean/mambaforge3:24.5.0-0-python3.12.4-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG GIT_ASKPASS
COPY git-ask-pass /

RUN pip install -U --no-cache-dir \
    boto3==1.38.27 \
    s3fs==2025.5.1 \
    spikeinterface[full]==0.105.2

COPY postInstall /
RUN --mount=type=secret,id=secrets . /run/secrets/secrets \
    && /postInstall
