"""
  This set of views are the 'about' pages of the CeNDR site
  and additional miscellaneous extra pages (e.g. getting started)
"""

import pandas as pd
import requests

from flask import Blueprint, render_template, url_for, request, redirect
from datetime import datetime, timezone
from caendr.services.logger import logger

# TODO: fix summaries
# from base.utils.query import get_mappings_summary, get_weekly_visits, get_unique_users

from config import config
from extensions import cache

from base.forms import DonationForm
from base.utils.auth import jwt_required, get_current_user
from base.utils.statistics import cum_sum_strain_isotype, get_strain_collection_plot, get_mappings_summary_legacy, get_report_sumary_plot_legacy, get_weekly_visits_plot, get_num_registered_users

from caendr.api.isotype import get_isotypes
from caendr.models.sql import Strain
from caendr.services.cloud.analytics import get_weekly_visits
from caendr.services.cloud.sheets import add_to_order_ws
from caendr.services.email import send_email, DONATION_SUBMISSION_EMAIL_TEMPLATE
from caendr.services.publication import get_publications_html_df
from caendr.services.profile import get_committee_profiles, get_staff_profiles, get_collaborator_profiles
from caendr.utils.data import load_yaml, get_object_hash

about_bp = Blueprint('about',
                    __name__,
                    template_folder='templates')


@about_bp.route('/')
@cache.memoize(60*60)
def about():
  ''' About us Page - Gives an overview of CeNDR '''
  title = "About CeNDR"
  disable_parent_breadcrumb = True
  isotypes = get_isotypes(known_origin=True, species='c_elegans')
  strain_listing = [s.to_json() for s in isotypes]
  return render_template('about/about.html', **locals())


@about_bp.route('/getting_started/')
@cache.memoize(60*60)
def getting_started():
  ''' Getting Started - provides information on how to get started with CeNDR '''
  title = "Getting Started"
  isotypes = get_isotypes(known_origin=True, species='c_elegans')
  strain_listing = [s.to_json() for s in isotypes]
  disable_parent_breadcrumb = True
  return render_template('about/getting_started.html', **locals())


@about_bp.route('/committee/')
@cache.memoize(60*60)
def committee():
  ''' Scientific Panel Page'''
  title = "Scientific Advisory Committee"
  disable_parent_breadcrumb = True
  profiles = get_committee_profiles()
  return render_template('about/committee.html', **locals())


@about_bp.route('/collaborators/')
@cache.memoize(60*60)
def collaborators():
  ''' Other Project Collaborators Page '''
  title = "Collaborators"
  disable_parent_breadcrumb = True
  profiles = get_collaborator_profiles()
  return render_template('about/collaborators.html', **locals())


@about_bp.route('/staff/')
@cache.memoize(60*60)
def staff():
  ''' Staff Page '''
  title = "Staff"
  disable_parent_breadcrumb = True
  profiles = get_staff_profiles()
  # Move director to top of list
  index = 0
  for i, item in enumerate(profiles):
    if hasattr(item, 'title') and item.title.lower() == 'director':
      p = profiles.pop(i)
      profiles.insert(0, p)
      break

  return render_template('about/staff.html', **locals())


@about_bp.route('/donate/', methods=['GET', 'POST'])
@jwt_required(optional=True)
def donate():
  ''' Process donation form page '''
  title = "Donate"
  disable_parent_breadcrumb = True
  form = DonationForm(request.form)

  # Autofill email
  user = get_current_user()
  if user and hasattr(user, 'email') and not form.email.data:
    form.email.data = user.email

  if form.validate_on_submit():
    # order_number is generated as a unique string
    order_obj = {
      "is_donation": True,
      "date": datetime.now(timezone.utc)
    }
    order_obj['items'] = u"{}:{}".format("CeNDR strain and data support", form.data.get('total'))
    order_obj.update(form.data)
    order_obj['invoice_hash'] = get_object_hash(order_obj, length=8)
    order_obj['url'] = url_for('order.order_confirmation', invoice_hash=order_obj['invoice_hash'], _external=True)
    send_email({
      "from": "no-reply@elegansvariation.org",
      "to": [order_obj["email"]],
      "cc": config.get("CC_EMAILS"),
      "subject": f"CeNDR Dontaion #{order_obj['invoice_hash']}",
      "text": DONATION_SUBMISSION_EMAIL_TEMPLATE.format(order_confirmation_link=order_obj.get('url'), donation_amount=order_obj.get('total'))
    })
    add_to_order_ws(order_obj)
    return redirect(url_for("order.order_confirmation", invoice_hash=order_obj["invoice_hash"]), code=302)
  return render_template('about/donate.html', **locals())


@about_bp.route('/funding/')
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


@about_bp.route('/publications')
@cache.memoize(60*60)
def publications():
  """  List of publications that have referenced CeNDR """
  title = "Publications"
  disable_parent_breadcrumb = True
  publications_html_df = get_publications_html_df()
  return render_template('about/publications.html', **locals())
