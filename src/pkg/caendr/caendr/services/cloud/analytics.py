import os
import json
import googleapiclient.discovery

from oauth2client.service_account import ServiceAccountCredentials
from base64 import b64decode

from caendr.services.cloud.secret import get_secret

GOOGLE_ANALYTICS_SERVICE_ACCOUNT_NAME = os.environ.get('GOOGLE_ANALYTICS_SERVICE_ACCOUNT_NAME')


def get_service_account_credentials():
  """ Fetch service account credentials for google analytics """
  sa_key = b64decode(get_secret(GOOGLE_ANALYTICS_SERVICE_ACCOUNT_NAME))
  return json.loads(sa_key)


def authenticate_google_analytics():
  """ Uses service account credentials to authorize access to google analytics """
  service_credentials = get_service_account_credentials()
  scope = ['https://www.googleapis.com/auth/analytics.readonly']
  credentials = ServiceAccountCredentials.from_json_keyfile_dict(service_credentials, scope)
  return googleapiclient.discovery.build('analyticsreporting', 'v4', credentials=credentials)

