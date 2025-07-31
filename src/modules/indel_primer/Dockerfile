FROM debian:11.11-slim

RUN apt update \
    && apt install -y --no-install-recommends \
      build-essential \
      gzip \
      curl \
      libz-dev \
      python3-dev \
      python3-pip \
      automake \
      autoconf \
      zlib1g-dev \
      libbz2-dev \
      liblzma-dev \
      libcurl4-gnutls-dev \
      libssl-dev \
      libncurses5-dev \
      wget \
      unzip \
      git \
    && apt autoremove \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*
    
RUN wget https://github.com/samtools/samtools/releases/download/1.22/samtools-1.22.tar.bz2 -O samtools.tar.bz2 \
    && tar -xjvf samtools.tar.bz2 \
    && cd samtools-1.22 && make && make prefix=/usr/local/bin install \
    && ln -s /usr/local/bin/bin/samtools /usr/bin/samtools \
    && cd ../ && rm -r samtools-1.22*

    RUN wget https://github.com/samtools/bcftools/releases/download/1.22/bcftools-1.22.tar.bz2 -O bcftools.tar.bz2 \
    && tar -xjvf bcftools.tar.bz2 \
    && cd bcftools-1.22 && make && make prefix=/usr/local/bin install \
    && ln -s /usr/local/bin/bin/bcftools /usr/bin/bcftools \
    && cd ../ && rm -r bcftools-1.22*

RUN wget https://github.com/samtools/htslib/releases/download/1.22/htslib-1.22.tar.bz2 -O htslib.tar.bz2 \
    && tar -xjvf htslib.tar.bz2 \
    && cd htslib-1.22 \
    && make && make install \
    && cd ../ && rm -r htslib-1.22*

COPY requirements.txt ./

RUN pip3 install -r requirements.txt && rm requirements.txt

RUN wget https://github.com/primer3-org/primer3/archive/refs/heads/main.zip \
    && unzip main.zip \
    && cd primer3-main/src \
    && make \
    && chmod a+x primer3_core \
    && mv primer3_core /usr/local/bin \
    && cd ../../ \
    && rm -rf primer3-main*

RUN wget https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/2.16.0/ncbi-blast-2.16.0+-x64-linux.tar.gz \
    && tar xzf ncbi-blast-2.16.0+-x64-linux.tar.gz \
    && mv ncbi-blast-2.16.0+/bin/blastn /usr/local/bin/ \
    && rm -rf ncbi-blast-2.16.0+*

RUN ln -s /usr/bin/python3 /usr/local/bin/python

COPY . /indel_primer/

RUN pip install --no-cache-dir -e /indel_primer/caendr

RUN git clone https://www.github.com/andersenlab/vcf-kit \
    && cd vcf-kit \
    && pip install --no-cache-dir . \
    && cd ../ \
    && rm -rf vcf-kit
