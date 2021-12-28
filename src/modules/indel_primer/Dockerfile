FROM continuumio/miniconda3

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      gzip \
      curl \
      libz-dev \
      procps && \
    apt-get autoremove && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

LABEL Name="indel-primer" Author="Daniel Cook"
WORKDIR /indel_primer

COPY env.yaml ./

# Create Conda environment
RUN conda env create -f ./env.yaml && conda clean -a
RUN echo "conda activate indel-primer" >> ~/.bashrc
ENV PATH /opt/conda/envs/indel-primer/bin:$PATH
ENV CONDA_DEFAULT_ENV indel-primer

# Now install VCF-Kit 0.2.8
RUN git clone https://www.github.com/andersenlab/vcf-kit && \
    cd vcf-kit && \
    git checkout f433abb637fe59a370f8c654ef406cbabaa36e0a


RUN python -m pip install --no-cache-dir -e ./vcf-kit
RUN vk genome wormbase --ref=WS276

COPY . ./

# Install requirements and CAENDR package
RUN python -m pip install --no-cache-dir -e ./caendr

