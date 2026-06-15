FROM python:3.13-slim

ENV PYTHONUNBUFFERED True

# Install production dependencies.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      libz-dev \
      virtualenv \
      wget && \
    apt-get autoremove && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV APP_HOME /db_operations
WORKDIR $APP_HOME

# make venv
RUN pip install virtualenv

RUN virtualenv --python=python3 venv
ENV VIRTUAL_ENV=$APP_HOME/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN python -m pip install --upgrade pip

COPY requirements.txt ./
COPY caendr caendr

# Install requirements and CAENDR package
RUN python -m pip install --no-cache-dir -r requirements.txt
RUN python -m pip install --no-cache-dir -e ./caendr

RUN wget https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.22.0/cloud-sql-proxy.linux.amd64 -O cloud-sql-proxy && \
    chmod u+x cloud-sql-proxy
RUN mkdir /cloudsql

# Copy local code to the container image.
COPY . ./
