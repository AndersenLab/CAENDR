import pandas as pd
import numpy as np
import arrow

from datetime import datetime

from caendr.models.sql import Strain
from caendr.services.cloud.postgresql import db
from caendr.services.cloud.datastore import query_ds_entities
from caendr.services.user import get_num_registered_users
from caendr.utils.plots import time_series_plot


def get_strain_collection_plot(df):
  return time_series_plot(
    df,
    x_title='Year',
    y_title='Count',
    range=[
      datetime(1995, 10, 17), 
      datetime.today()
    ]
  )
  

def cum_sum_strain_isotype():
  """
      Create a time-series plot of strains and isotypes collected over time

      Args:
          df - the strain dataset
  """
  df = pd.read_sql_table(Strain.__tablename__, db.engine)
  # Remove strains with issues
  df = df[df["issues"] == False]
  cumulative_isotype = df[['isotype', 'sampling_date']].sort_values(['sampling_date'], axis=0) \
                                                        .drop_duplicates(['isotype']) \
                                                        .groupby(['sampling_date'], as_index=True) \
                                                        .count() \
                                                        .cumsum() \
                                                        .reset_index()
  cumulative_isotype = cumulative_isotype.append({'sampling_date': np.datetime64(datetime.today().strftime("%Y-%m-%d")),
                                                  'isotype': len(df['isotype'].unique())}, ignore_index=True)
  cumulative_strain = df[['strain', 'sampling_date']].sort_values(['sampling_date'], axis=0) \
                                                      .drop_duplicates(['strain']) \
                                                      .dropna(how='any') \
                                                      .groupby(['sampling_date']) \
                                                      .count() \
                                                      .cumsum() \
                                                      .reset_index()
  cumulative_strain = cumulative_strain.append({'sampling_date': np.datetime64(datetime.today().strftime("%Y-%m-%d")),
                                                'strain': len(df['strain'].unique())}, ignore_index=True)
  df = cumulative_isotype.set_index('sampling_date') \
                          .join(cumulative_strain.set_index('sampling_date')) \
                          .reset_index()
  return df
  
  
def get_report_sumary_plot_legacy(df):
  return time_series_plot(
    df,
    x_title='Date',
    y_title='Count',
    range=[
      datetime(2016, 3, 1),
      datetime.today()
    ],
    colors=[
      'rgb(149, 150, 255)', 
      'rgb(81, 151, 35)'
    ]
  )


def get_mappings_summary_legacy():
  """
      Generates the cumulative sum of reports and traits mapped.
      Cached daily
  """
  traits = query_ds_entities('trait')
  if traits:
    traits = pd.DataFrame.from_dict(traits)
    if 'created_on' in traits.columns and 'report_slug' in traits.columns:
      traits.created_on = traits.apply(lambda x: arrow.get(str(x['created_on'])[:-6]).date().isoformat(), axis=1)
      trait_df = traits.groupby('created_on').size().reset_index(name='traits')
      report_df = traits[['report_slug', 'created_on']].drop_duplicates().groupby('created_on').size().reset_index(name='reports')
      df = pd.merge(report_df, trait_df, how='outer').fillna(0).sort_values('created_on')
      df.reports = df.reports.cumsum()
      df.traits = df.traits.cumsum()
      return df
  
  return pd.DataFrame()


def get_weekly_visits_plot(df):
  return time_series_plot(
    df,
    x_title='Date',
    y_title='Count',
    range=[
      datetime(2016, 3, 1),
      datetime.today()
    ],
    colors=['rgb(255, 204, 102)']
  )