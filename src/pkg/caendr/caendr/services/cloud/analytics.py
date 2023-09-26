import os
import json
import pandas as pd

from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

from caendr.services.cloud.secret import get_secret
from caendr.services.cloud.service_account import get_service_account_credentials
from caendr.utils.env import get_env_var

from .discovery import use_service



GOOGLE_ANALYTICS_SERVICE_ACCOUNT_NAME = get_env_var('GOOGLE_ANALYTICS_SERVICE_ACCOUNT_NAME')



def get_analytics_credentials():
  '''
    Helper function to get the service account credentials that authorize access to Google Analytics
  '''
  service_credentials = get_service_account_credentials(get_secret(GOOGLE_ANALYTICS_SERVICE_ACCOUNT_NAME))
  scope = ['https://www.googleapis.com/auth/analytics.readonly']
  return ServiceAccountCredentials.from_json_keyfile_dict(service_credentials, scope)


@use_service('analyticsreporting', 'v4', credentials=get_analytics_credentials)
def get_weekly_visits(SERVICE):
  """
      Get the number of weekly visitors
      Cached weekly
  """
  response = SERVICE.reports().batchGet(
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
