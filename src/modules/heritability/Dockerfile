FROM continuumio/miniconda3


RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      libz-dev \
      procps && \
    apt-get autoremove && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY env.yaml ./

# Create Conda environment
RUN conda env create -f ./env.yaml && conda clean -a
RUN echo "conda activate heritability" >> ~/.bashrc
ENV PATH /opt/conda/envs/heritability/bin:$PATH
ENV CONDA_DEFAULT_ENV heritability

LABEL Name="heritability" Author="Daniel Cook"
WORKDIR /h2

COPY . ./

# Install requirements and CAENDR package
RUN python -m pip install --no-cache-dir -e ./caendr

