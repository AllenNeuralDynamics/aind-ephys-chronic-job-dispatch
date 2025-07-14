# hash:sha256:ea5d229a697fee21797ad9ea7a9949d14a9d17a5f5dd12bf323ac2648dfabce5
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
    s3fs==2025.5.1 \
    spikeinterface[full]==0.102.3

COPY postInstall /
RUN /postInstall
