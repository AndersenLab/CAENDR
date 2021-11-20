FROM python:3.9-slim

ENV PYTHONUNBUFFERED True

# Install production dependencies.
RUN apt-get update && \
    apt-get upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        python3-virtualenv \
        virtualenv \
        wget && \
    apt-get autoremove && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV APP_HOME /db_operations
WORKDIR $APP_HOME

# make venv
RUN virtualenv --python=python3 venv
ENV VIRTUAL_ENV=$APP_HOME/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN python -m pip install --upgrade pip

# Copy local code to the container image.
COPY . ./

# Install requirements and CAENDR package
RUN python -m pip install --no-cache-dir -r requirements.txt
RUN python -m pip install --no-cache-dir -e ./caendr

RUN wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O cloud_sql_proxy && \
    chmod u+x cloud_sql_proxy 

