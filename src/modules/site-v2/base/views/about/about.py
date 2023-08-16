"""
  This set of views are the 'about' pages of the CeNDR site
  and additional miscellaneous extra pages (e.g. getting started)
"""

from math import isnan
from flask import Blueprint, render_template
from caendr.services.logger import logger

# TODO: fix summaries
# from base.utils.query import get_mappings_summary, get_weekly_visits, get_unique_users

from extensions import cache

from base.utils.statistics import cum_sum_strain_isotype, get_strain_collection_plot, get_mappings_summary_legacy, get_report_sumary_plot_legacy, get_weekly_visits_plot, get_num_registered_users

from caendr.api.isotype import get_isotypes
from caendr.models.datastore.species import Species
from caendr.models.datastore.profile import Profile
from caendr.services.cloud.analytics import get_weekly_visits
from caendr.services.publication import get_publications_html_df
from caendr.utils.data import load_yaml


about_bp = Blueprint(
  'about', __name__, template_folder='templates'
)


@about_bp.route('/')
@cache.memoize(60*60)
def about():
  ''' About us Page - Gives an overview of CaeNDR '''

  try:
    strain_listing = [s.to_json() for s in get_isotypes(known_origin=True)]
  except Exception as ex:
    logger.error(f'Failed to retrieve strain list: {ex}')
    strain_listing = None

  return render_template('about/about.html', **{
    'title': 'About CaeNDR',
    'disable_parent_breadcrumb': True,
    'strain_listing': strain_listing,
  })


@about_bp.route('/getting_started')
@cache.memoize(60*60)
def getting_started():
  ''' Getting Started - provides information on how to get started with CeNDR '''

  try:
    strain_listing = [s.to_json() for s in get_isotypes(known_origin=True)]
  except Exception as ex:
    logger.error(f'Failed to retrieve strain list: {ex}')
    strain_listing = None

  return render_template('about/getting_started.html', **{
    'title': "Getting Started",
    'disable_parent_breadcrumb': True,
    'strain_listing': strain_listing,
  })


@about_bp.route('/people')
@cache.memoize(60*60)
def people():

  # Get all profiles
  profiles = {
    role.code: Profile.query_ds_roles( role ) for role in Profile.all_roles()
  }

  # Move director to top of staff list
  for i, item in enumerate(profiles[Profile.STAFF.code]):
    if hasattr(item, 'title') and item.title.lower() == 'director':
      p = profiles[Profile.STAFF.code].pop(i)
      profiles[Profile.STAFF.code].insert(0, p)
      break

  return render_template('about/people.html', **{
    'title': "People",
    'disable_parent_breadcrumb': True,

    'Profile': Profile,
    'profiles': profiles,
  })


@about_bp.route('/funding')
@cache.memoize(60*60)
def funding():
  title = "Funding"
  disable_parent_breadcrumb = True
  funding_set = load_yaml('funding.yaml')
  return render_template('about/funding.html', **locals())


@about_bp.route('/statistics')
@cache.memoize(60*60*24)
def statistics():
  title = "Statistics"

  # Strain collections plot
  ##########################
  df = cum_sum_strain_isotype()
  try:
    n_strains = {
      species_name: max(df[f'{species_name}_strain']) for species_name in Species.all()
    }
    n_strains = sum([ n for _, n in n_strains.items() if not isnan(n) ])
    n_isotypes = {
      species_name: max(df[f'{species_name}_isotype']) for species_name in Species.all()
    }
    n_isotypes = sum([ n for _, n in n_isotypes.items() if not isnan(n) ])
    strain_collection_plot = get_strain_collection_plot(df)
  except AttributeError:
    n_strains = 0
    n_isotypes = 0
    strain_collection_plot = None

  # Reports plot
  ##########################
  df = get_mappings_summary_legacy()
  try:
    n_reports = int(max(df.reports))
    n_traits = int(max(df.traits))
    report_summary_plot = get_report_sumary_plot_legacy(df)
  except AttributeError:
    n_reports = 0
    n_traits = 0
    report_summary_plot = None

  
  # Weekly visits plot
  ################################
  try:
    df = get_weekly_visits()
    weekly_visits_plot = get_weekly_visits_plot(df)
  except Exception as e:
    logger.warn("Unable to fetch weekly visits from Google Analytics")
    df = None
    weekly_visits_plot = None


  # Unique users
  ############################
  n_users = get_num_registered_users()
  VARS = {
    'title': title,
    'disable_parent_breadcrumb': True,
    'strain_collection_plot': strain_collection_plot,
    'report_summary_plot': report_summary_plot,
    'weekly_visits_plot': weekly_visits_plot,
    'n_strains': n_strains,
    'n_isotypes': n_isotypes,
    'n_users': n_users,
    'n_reports': n_reports,
    'n_traits': n_traits
  }
  return render_template('about/statistics.html', **VARS)


@about_bp.route('/cited-by')
@cache.memoize(60*60)
def cited_by():
  """  List of publications that have referenced CeNDR """
  title = "Cited By"
  disable_parent_breadcrumb = True
  publications_html_df = get_publications_html_df()
  return render_template('about/publications.html', **locals())


@about_bp.route('/contact-us')
@cache.memoize(60*60)
def contact_us():
  title = "Contact Us"
  return render_template('about/contact-us.html', **locals())