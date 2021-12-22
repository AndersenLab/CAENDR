import os
import json
import googleapiclient.discovery
import pandas as pd

from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from base64 import b64decode

from caendr.services.cloud.secret import get_secret
from caendr.services.cloud.service_account import get_service_account_credentials

GOOGLE_ANALYTICS_SERVICE_ACCOUNT_NAME = os.environ.get('GOOGLE_ANALYTICS_SERVICE_ACCOUNT_NAME')


def authenticate_google_analytics():
  """ Uses service account credentials to authorize access to google analytics """
  service_credentials = get_service_account_credentials(get_secret(GOOGLE_ANALYTICS_SERVICE_ACCOUNT_NAME))
  scope = ['https://www.googleapis.com/auth/analytics.readonly']
  credentials = ServiceAccountCredentials.from_json_keyfile_dict(service_credentials, scope)
  return googleapiclient.discovery.build('analyticsreporting', 'v4', credentials=credentials)


def get_weekly_visits():
  """
      Get the number of weekly visitors
      Cached weekly
  """
  ga = authenticate_google_analytics()
  response = ga.reports().batchGet(
    body={
      'reportRequests': [{
        'viewId': '117392266',
        'dateRanges': [{'startDate': '2015-01-01', 'endDate': datetime.now().date().isoformat()}],
        'metrics': [{'expression': 'ga:sessions'}],
        'dimensions': [{'name': 'ga:year'}, {'name': 'ga:week'}],
        'orderBys': [{"fieldName": "ga:sessions", "sortOrder": "DESCENDING"}],
        'pageSize': 10000
      }]
    }
  ).execute()
  out = []
  for row in response['reports'][0]['data']['rows']:
    ymd = f"{row['dimensions'][0]}-W{row['dimensions'][1]}-0"
    date = datetime.strptime(ymd, "%Y-W%W-%w")
    out.append({'date': date, 'count': row['metrics'][0]['values'][0]})
  df = pd.DataFrame(out) \
          .sort_values('date') \
          .reindex(['date', 'count'], axis=1)
  df['count'] = df['count'].astype(int)
  df['count'] = df['count'].dropna().cumsum()
  return df
