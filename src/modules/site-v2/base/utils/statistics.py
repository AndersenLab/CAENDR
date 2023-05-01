import pandas as pd
import numpy as np
import arrow

from datetime import datetime

from caendr.models.datastore.species import SPECIES_LIST
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


# TODO: Handle gaps
def cum_vals(df, column, dropna=False, sampling_date_as_index=False):

  # Get column of interest, sort by date, and drop duplicates
  result = df[[column, 'sampling_date']]       \
      .sort_values(['sampling_date'], axis=0)  \
      .drop_duplicates([column])

  # Drop null values, if applicable
  if (dropna):
    result = result.dropna(how='any')

  # Not sure why you can't just pass the boolean as an argument, but it breaks if you do
  if (sampling_date_as_index):
    result = result.groupby(['sampling_date'], as_index=sampling_date_as_index)
  else:
    result = result.groupby(['sampling_date'])

  # Count the number of items and convert to a cumulative sum
  result = result.count().cumsum().reset_index()

  # Add data point for current date
  result = result.append({
    'sampling_date': np.datetime64(datetime.today().strftime("%Y-%m-%d")),
    column: len(df[column].unique())
  }, ignore_index=True)

  return result



def cum_sum_strain_isotype():
  """
      Create a time-series plot of strains and isotypes collected over time

      Args:
          df - the strain dataset
  """
  df = pd.read_sql_table(Strain.__tablename__, db.engine)

  # Remove strains with issues
  df = df[df["issues"] == False]

  # Loop through all species, adding to result frame
  result = None
  for species_name in SPECIES_LIST:

    # Filter data frame by current species
    species_frame = df[df["species_name"] == species_name]

    # Get cumulative sums for isotypes and strain
    cum_isotypes = cum_vals(species_frame, 'isotype', dropna=False, sampling_date_as_index=True ).set_index('sampling_date')
    cum_strains  = cum_vals(species_frame, 'strain',  dropna=True,  sampling_date_as_index=False).set_index('sampling_date')

    # Add cumulative isotype & strain counts to result
    if result is None:
      result = cum_isotypes.join(cum_strains)
    else:
      result = result.join(cum_isotypes).join(cum_strains)

    result = result.rename(columns={
      'isotype': f'{species_name}_isotype',
      'strain':  f'{species_name}_strain',
    })

  # Reset the index
  result = result.reset_index()

  return result
  
  
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