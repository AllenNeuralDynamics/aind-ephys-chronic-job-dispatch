# hash:sha256:e1d1656ec4521ad6eedb655482f2be3c327eb3bfd8006ff35402bf629721d10d
ARG REGISTRY_HOST
FROM $REGISTRY_HOST/codeocean/mambaforge3:24.5.0-0-python3.12.4-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive

ARG GIT_ASKPASS
ARG GIT_ACCESS_TOKEN
COPY git-askpass /

RUN conda install -y \
        jupyterlab==4.4.4 \
    && conda clean -ya

RUN pip install -U --no-cache-dir \
    boto3==1.38.27 \
    s3fs==2025.5.1 \
    spikeinterface[full]==0.102.3

COPY postInstall /
RUN /postInstall
