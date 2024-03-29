# Use the official lightweight Python image.
FROM python:3.9-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Install production dependencies.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      libbz2-dev \
      libssl-dev \
      liblzma-dev \
      libz-dev \
      tabix \
      libcurl4-openssl-dev \
      virtualenv && \
    apt-get autoremove && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create src directory
ENV APP_HOME /api_pipeline_task
WORKDIR $APP_HOME

# make venv
RUN pip install virtualenv

RUN virtualenv --python=python3 venv
ENV VIRTUAL_ENV $APP_HOME/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH $VIRTUAL_ENV/bin:$PATH
RUN python -m pip install --upgrade pip

COPY requirements.txt .

# Install python modules from requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY caendr caendr

RUN python -m pip install --no-cache-dir -e ./caendr

# Copy local code to the container image.
COPY . ./

# Inject the git commit into the file $WORKDIR/module.env
ARG GIT_COMMIT=GIT_COMMIT_NOT_AVAILABLE
RUN echo "\n\n# GIT_COMMIT automatically added during the makefile build container" >> module.env
RUN echo "GIT_COMMIT=$GIT_COMMIT" >> module.env

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
# Timeout is set to 0 to disable the timeouts of the workers to allow Cloud Run to handle instance scaling.

CMD export $(cat .env | sed -e '/^\s*$/d' | sed -e '/^\#/d' | xargs) && \
    exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
