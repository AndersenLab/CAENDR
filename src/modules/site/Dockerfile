FROM gcr.io/google-appengine/python

ENV PYTHONUNBUFFERED True

# Install production dependencies.
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    fuse \
    git \
    graphviz \
    gunicorn \
    libbz2-dev \
    libgraphviz-dev \
    liblzma-dev \
    libncursesw5-dev \
    libncurses5-dev \
    libxml2 \
    libxml2-dev \
    libxmlsec1-dev \
    libxmlsec1-openssl \
    make \
    pkg-config \
    python3 \
    python3-venv \
    python3-virtualenv \
    tabix \
    virtualenv \
    xmlsec1 \
    zlib1g-dev && \
  apt-get autoremove && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

ENV APP_HOME /site
WORKDIR $APP_HOME

RUN mkdir /gcloud
RUN cd /gcloud && curl -O "https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-380.0.0-linux-x86_64.tar.gz" && tar xvzf google-cloud-sdk-380.0.0-linux-x86_64.tar.gz

# make venv
ENV VIRTUAL_ENV $APP_HOME/venv
RUN virtualenv -p python3 $VIRTUAL_ENV
ENV PATH $VIRTUAL_ENV/bin:$PATH
RUN python -m pip install --upgrade pip

# Copy local code to container image
COPY . ./

# Install python modules from pip
RUN python -m pip install --no-cache-dir -r requirements.txt
RUN python -m pip install --no-cache-dir -e ./caendr

CMD export $(cat .env | sed -e '/^\s*$/d' | sed -e '/^\#/d' | xargs) && \
  gunicorn -b :$PORT main:app
