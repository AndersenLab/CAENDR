import os
import pandas as pd

from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

from caendr.services.cloud.secret import get_secret
from caendr.services.cloud.service_account import get_service_account_credentials
from caendr.services.cloud.storage import get_blob, download_blob_as_dataframe
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


@use_service('analyticsdata', 'v1beta', credentials=get_analytics_credentials)
def get_weekly_visits_ga4(SERVICE):
  """ Get reports from Google Analytics 4 """

  property_id = '361534565'
  property = f"properties/{property_id}"
  request = {
    "dateRanges": [
    {
        "startDate": "2023-04-01",
        "endDate": "today"
    }
    ],
    "dimensions": [{'name': 'year'}, {'name': 'week'}],
    "metrics": [{'name': 'sessions'}],
    'orderBys': {
      'desc': True,
      'metric': {
        'metricName': 'sessions'
      }
    }
  }
  response = SERVICE.properties().runReport(property=property, body=request).execute()
  out = []
  for row in response['rows']:
    ymd = f"{row['dimensionValues'][0]['value']}-W{row['dimensionValues'][1]['value']}-0"
    date = datetime.strptime(ymd, "%Y-W%W-%w")
    out.append({'date': date, 'count': row['metricValues'][0]['value']})
  df = pd.DataFrame(out) \
          .sort_values('date') \
          .reindex(['date', 'count'], axis=1)
  
  """ 
    Get the Universal Analytics (UA) report file generated using get_weekly_visits() function (later deprecated, structured the same way as the above dataframe) for dates 2016/03/01 - 2023/03/31 
    and combine it with Google Analytics 4 (GA4) for dates 2023/04/01 - today

    *** UA had been tracking data for CaeNDR before 2023/03/31
        Starting 2023/04/01 it was migrated to GA4.
        UA stopped proccessing data starting 2023/07/01.
  """
  
  MODULE_SITE_BUCKET_PRIVATE_NAME = os.environ.get('MODULE_SITE_BUCKET_PRIVATE_NAME')

  # Get the CSV file from buckets
  blob = get_blob(MODULE_SITE_BUCKET_PRIVATE_NAME, 'ga_reports/archived_ga_data_for_plot.csv')

  # Convert the blob to dataframe and merge it with GA4 data
  df_archived = download_blob_as_dataframe(blob, sep=',')
  merged_df = pd.concat([df_archived, df], axis=0)
  merged_df['count'] = merged_df['count'].astype(int)
  merged_df['count'] = merged_df['count'].dropna().cumsum()
  return merged_df
