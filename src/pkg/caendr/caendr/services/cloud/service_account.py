import json
import googleapiclient.discovery

from base64 import b64decode
from oauth2client.service_account import ServiceAccountCredentials


def get_service_account_credentials(sa_private_key_secret):
  """ Fetch service account credentials for service account with JSON private key stored as a cloud secret"""
  sa_key = b64decode(sa_private_key_secret)
  return json.loads(sa_key)


def authenticate_google_service(sa_private_key_secret: str, scope_list: 'list[str]', service_name: str, version: str='v4'):
  """ Uses service account credentials to authorize access to google services """
  service_credentials = get_service_account_credentials(sa_private_key_secret)
  scope = scope_list
  credentials = ServiceAccountCredentials.from_json_keyfile_dict(service_credentials, scope)
  return googleapiclient.discovery.build(service_name, version, credentials=credentials)

