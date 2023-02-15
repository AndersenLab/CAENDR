"""
  This set of views are the 'about' pages of the CeNDR site
  and additional miscellaneous extra pages (e.g. getting started)
"""

from flask import Blueprint, render_template
from caendr.services.logger import logger

# TODO: fix summaries
# from base.utils.query import get_mappings_summary, get_weekly_visits, get_unique_users

from extensions import cache

from base.utils.statistics import cum_sum_strain_isotype, get_strain_collection_plot, get_mappings_summary_legacy, get_report_sumary_plot_legacy, get_weekly_visits_plot, get_num_registered_users

from caendr.api.isotype import get_isotypes
from caendr.services.cloud.analytics import get_weekly_visits
from caendr.services.publication import get_publications_html_df
from caendr.services.profile import get_committee_profiles, get_staff_profiles, get_collaborator_profiles
from caendr.utils.data import load_yaml


about_bp = Blueprint(
  'about', __name__, template_folder='templates'
)


@about_bp.route('/')
@cache.memoize(60*60)
def about():
  ''' About us Page - Gives an overview of CaeNDR '''
  title = "About CaeNDR"
  disable_parent_breadcrumb = True
  isotypes = get_isotypes(known_origin=True, species='c_elegans')
  strain_listing = [s.to_json() for s in isotypes]
  return render_template('about/about.html', **locals())


@about_bp.route('/getting_started')
@cache.memoize(60*60)
def getting_started():
  ''' Getting Started - provides information on how to get started with CeNDR '''
  title = "Getting Started"
  isotypes = get_isotypes(known_origin=True, species='c_elegans')
  strain_listing = [s.to_json() for s in isotypes]
  disable_parent_breadcrumb = True
  return render_template('about/getting_started.html', **locals())


@about_bp.route('/people')
@cache.memoize(60*60)
def people():
  '''
    People
  '''
  title = "People"
  disable_parent_breadcrumb = True

  profiles = {
    'committee':     get_committee_profiles(),
    'collaborators': get_collaborator_profiles(),
    'staff':         get_staff_profiles(),
  }

  # Move director to top of staff list
  for i, item in enumerate(profiles['staff']):
    if hasattr(item, 'title') and item.title.lower() == 'director':
      p = profiles['staff'].pop(i)
      profiles['staff'].insert(0, p)
      break

  return render_template('about/people.html', **locals())


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
    n_strains = max(df.strain)
    n_isotypes = max(df.isotype)
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
