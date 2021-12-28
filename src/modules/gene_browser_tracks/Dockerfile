FROM continuumio/miniconda3

ENV PYTHONUNBUFFERED True

RUN echo "deb http://security.debian.org/debian-security jessie/updates main" >> /etc/apt/sources.list

# Install production dependencies.
RUN apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
      apt-transport-https \
      ca-certificates \
      curl \
      gawk \
      gnupg \
      libssl1.0.0 \
      tabix \
      vim

RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
  curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - && \
  apt-get update -y && \
  apt-get install google-cloud-sdk -y && \
  apt-get autoremove && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

# Create src directory
ENV APP_HOME /gene_browser_tracks
WORKDIR $APP_HOME

# Copy local code to the container image.
COPY . ./

RUN conda env update -n root -f conda.yml \
  && conda clean -a
