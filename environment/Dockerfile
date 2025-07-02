# hash:sha256:6e823d40786e13800600e75ccfcae12532b0c8d27b19e945bc36f4b27bea7358
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
    spikeinterface[full]==0.102.3

COPY postInstall /
RUN /postInstall
