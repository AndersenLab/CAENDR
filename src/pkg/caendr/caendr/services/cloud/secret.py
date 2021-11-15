import os
from google.cloud import secretmanager

GOOGLE_CLOUD_PROJECT_NUMBER = os.environ.get('GOOGLE_CLOUD_PROJECT_NUMBER')
SECRETS_IDS = [
  'ANDERSEN_LAB_STRAIN_SHEET',
  'CENDR_PUBLICATIONS_SHEET',
  'ELEVATION_API_KEY',
  'GOOGLE_CLIENT_ID',
  'GOOGLE_CLIENT_SECRET',
  'JWT_SECRET_KEY',
  'PASSWORD_SALT',
  'POSTGRES_DB_PASSWORD',
  'RECAPTCHA_PUBLIC_KEY',
  'RECAPTCHA_PRIVATE_KEY',
  'SECRET_KEY',
  'MAILGUN_API_KEY'
]

secretManagerClient = secretmanager.SecretManagerServiceClient()

def get_secret(id, version='latest'):
    secretName = f"projects/{GOOGLE_CLOUD_PROJECT_NUMBER}/secrets/{id}/versions/{version}"
    response = secretManagerClient.access_secret_version(request={"name": secretName})
    secret = response.payload.data.decode("UTF-8")
    return secret
