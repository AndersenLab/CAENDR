FROM python:3.8-slim-buster

ENV PYTHONUNBUFFERED True

ENV APP_HOME /maintenance
WORKDIR $APP_HOME

# ENV VIRTUAL_ENV $APP_HOME/venv
# RUN virtualenv -p python3 $VIRTUAL_ENV
# ENV PATH $VIRTUAL_ENV/bin:$PATH
RUN python -m pip install --upgrade pip

COPY . ./

RUN python -m pip install --no-cache-dir -r requirements.txt

CMD export $(cat .env | sed -e '/^\s*$/d' | sed -e '/^\#/d' | xargs) && \
  gunicorn -b :$PORT main:app
