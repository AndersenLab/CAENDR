import os
import json
import requests

from datetime import datetime
from caendr.services.logger import logger
from flask import Flask, render_template, request, redirect
from flask_wtf.csrf import CSRFProtect
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import exc
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import HTTPException

from config import config
import pytz

from caendr.models.error import BasicAuthError
from caendr.services.cloud.postgresql import db, health_database_status
from base.utils.markdown import render_markdown, render_ext_markdown



# --------- #
#  Routing  #
# --------- #
from base.views import primary_bp
from base.views import strains_bp
from base.views import user_bp
from base.views import isotype_bp

# Data
from base.views.data import data_bp
from base.views.data import releases_bp
from base.views.data import data_downloads_bp

# Tool
from base.views.tools import tools_bp
from base.views.tools import genome_browser_bp
from base.views.tools import variant_annotation_bp
from base.views.tools import genetic_mapping_bp
from base.views.tools import pairwise_indel_finder_bp
from base.views.tools import heritability_calculator_bp
from base.views.tools import phenotype_comparison_bp
from base.views.tools import phenotype_database_bp

# About & Get Involved
from base.views.about        import about_bp
from base.views.get_involved import get_involved_bp

# API
from base.views.api import api_gene_bp, api_notifications_bp, api_trait_bp

# Admin
from base.views.admin import admin_bp
from base.views.admin import admin_users_bp
from base.views.admin import admin_dataset_bp
from base.views.admin import admin_profile_bp
from base.views.admin import admin_tools_bp
from base.views.admin import admin_etl_op_bp
from base.views.admin import admin_gene_browser_tracks_bp
from base.views.admin import admin_content_bp
from base.views.admin import admin_system_bp


# Maintenance
from base.views.maintenance import maintenance_bp

# Auth
from base.views.auth import (auth_bp, 
                            google_bp)


'''
from base.views.gene import gene_bp
from base.views.admin.admin import admin_bp

'''




# Readiness and health checks
from base.views import check_bp

'''
# API
from base.views.api.api_strain import api_strain_bp
from base.views.api.api_variant import api_variant_bp
from base.views.api.api_data import api_data_bp
'''


# ---- End Routing ---- #

# Extensions
from extensions import (
  markdown,
  cache,
  debug_toolbar,
  sslify,
  sqlalchemy,
  jwt,
  compress
)

from caendr.utils.env import get_env_var
from caendr.services.cloud.secret import get_secret

MODULE_SITE_HOST = get_env_var('MODULE_SITE_HOST')


def create_app(config=config):
  """Returns an initialized Flask application."""
  app = Flask(__name__,
              static_url_path='/static',
              static_folder='base/static',
              template_folder='templates')

  # Fix wsgi proxy
  app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
  app.config.update(config)

  register_blueprints(app)
  register_template_filters(app)
  register_extensions(app)
  register_errorhandlers(app)
  register_request_handlers(app)
  configure_jinja(app)
  configure_ssl(app)

  password_protect_site(app)

  # app.teardown_request(close_active_connections)

  db_connection_status, db_test_output = health_database_status()
  logger.info(f"Database Connection: { 'OK' if db_connection_status else 'Error' }. {db_test_output}")

  return app



def configure_ssl(app):
  """Configure SSL"""
  if os.getenv('HOME') == "/root":
    # Running on server
    app.debug = False
    # Ignore leading slash of urls; skips must use start of path
    sslify(app, skips=['tasks'])
  elif app.config['DEBUG']:
    debug_toolbar(app)
    app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = True


# Template filters
def comma(value):
  return "{:,.0f}".format(value)

def format_release(value):
  return datetime.strptime(str(value), '%Y%m%d').strftime('%Y-%m-%d')

def get_status_css_class(value):
  mapping = {
    'COMPLETE': 'bg-success',
    'ERROR': 'bg-danger',
    'SUBMITTED': 'bg-info',
    'RUNNING': 'bg-primary'
  }
  return mapping.get(value, '')

# similar to the git short hash
def short_hash(hash):
  return hash[0:8]

def register_template_filters(app):
  for t_filter in [comma, format_release, get_status_css_class, short_hash]:
    app.template_filter()(t_filter)

def register_extensions(app):
  markdown(app)
  cache.init_app(app, config={'CACHE_TYPE': 'base.utils.cache.datastore_cache'})
  sqlalchemy.init_app(app)
  # protect all routes (except the ones listed) from cross site request forgery
  csrf = CSRFProtect(app)
  csrf.exempt(auth_bp)
  csrf.exempt(maintenance_bp)
  app.config['csrf'] = csrf
  jwt.init_app(app)
  compress.init_app(app)


def register_blueprints(app):
  """Register blueprints with the Flask application."""
  app.register_blueprint(primary_bp, url_prefix='')
  app.register_blueprint(about_bp, url_prefix='/about')
  app.register_blueprint(strains_bp, url_prefix='/request-strains')
  app.register_blueprint(isotype_bp, url_prefix='/isotype')
  app.register_blueprint(get_involved_bp, url_prefix='/get-involved')

  # Data
  app.register_blueprint(data_bp, url_prefix='/data')
  app.register_blueprint(releases_bp, url_prefix='/data/data-release')
  app.register_blueprint(data_downloads_bp, url_prefix='/data')
  
  # User
  app.register_blueprint(user_bp, url_prefix='/user')
  
  # Admin
  app.register_blueprint(admin_bp, url_prefix='/admin')
  app.register_blueprint(admin_users_bp, url_prefix='/admin/users')
  app.register_blueprint(admin_dataset_bp, url_prefix='/admin/datasets')
  app.register_blueprint(admin_profile_bp, url_prefix='/admin/profiles')
  app.register_blueprint(admin_tools_bp, url_prefix='/admin/tools')
  app.register_blueprint(admin_etl_op_bp, url_prefix='/admin/etl')
  app.register_blueprint(admin_gene_browser_tracks_bp, url_prefix='/admin/gene_browser_tracks')
  app.register_blueprint(admin_content_bp, url_prefix='/admin/content')
  app.register_blueprint(admin_system_bp, url_prefix='/admin/system')
  
  # Healthchecks/Maintenance
  app.register_blueprint(maintenance_bp, url_prefix='/tasks')
  app.register_blueprint(check_bp, url_prefix='')
  
  # API
  app.register_blueprint(api_gene_bp,          url_prefix='/api')
  app.register_blueprint(api_notifications_bp, url_prefix='/api/notifications')
  app.register_blueprint(api_trait_bp,         url_prefix='/api/trait')

  
  # Auth
  app.register_blueprint(auth_bp, url_prefix='/auth')
  app.register_blueprint(google_bp, url_prefix='/login')
  
  # Tools
  app.register_blueprint(tools_bp, url_prefix='/tools')
  app.register_blueprint(genome_browser_bp,          url_prefix='/tools/genome-browser')
  app.register_blueprint(variant_annotation_bp,      url_prefix='/tools/variant-annotation')
  app.register_blueprint(genetic_mapping_bp,         url_prefix='/tools/genetic-mapping')
  app.register_blueprint(pairwise_indel_finder_bp,   url_prefix='/tools/pairwise-indel-finder')
  app.register_blueprint(heritability_calculator_bp, url_prefix='/tools/heritability-calculator')
  # app.register_blueprint(phenotype_comparison_bp,    url_prefix='/tools/phenotype-comparison')
  app.register_blueprint(phenotype_database_bp,      url_prefix='/tools/phenotype-database')

  '''
  app.register_blueprint(gene_bp, url_prefix='/gene')
  

  # API
  app.register_blueprint(api_strain_bp, url_prefix='/api')
  app.register_blueprint(api_variant_bp, url_prefix='/api')
  app.register_blueprint(api_data_bp, url_prefix='/api')
'''



MODULE_SITE_BUCKET_ASSETS_NAME = os.environ.get('MODULE_SITE_BUCKET_ASSETS_NAME')
def ext_asset(path):
  return f"https://storage.googleapis.com/{MODULE_SITE_BUCKET_ASSETS_NAME}/{path}"

ENV = os.environ.get("ENV")
def get_env():
  return ENV or None


def configure_jinja(app):
  # Injects "contexts" into templates
  @app.context_processor
  def inject():
    return dict(
      version=f"{os.environ.get('MODULE_NAME', 'NONE')}-{os.environ.get('MODULE_VERSION', '9-9-9-9')}",
      json=json,
      list=list,
      str=str,
      int=int,
      len=len,
      ext_asset=ext_asset,
      get_env=get_env,
      basename=os.path.basename,
      render_markdown=render_markdown,
      render_ext_markdown=render_ext_markdown
    )

  #  2021-04-14 17:26:51.348674+00:00
  #  '%Y-%m-%d %H:%M:%S.%f+%z'
  # Datetime filters for Jinja
  @app.template_filter('date_format')
  def _jinja2_filter_datetime(date, fmt=None):
    timezone_name = config.get('TIMEZONE', 'America/Chicago')
    timezone = pytz.timezone(timezone_name)
    aware_date = date.astimezone(timezone)

    if fmt:
      return aware_date.strftime(fmt)
    else:
      return aware_date.strftime('%Y-%m-%d %I:%M %p %z')
    
  @app.template_filter('species_italic')
  def _jinja2_filter_species_italic(text):
    text = text.replace('C. briggsae', '<i>C. briggsae</i>')
    text = text.replace('C. elegans', '<i>C. elegans</i>')
    return text

  @app.template_filter('percent')
  def _jinja2_filter_percent(n):
    return f'{round(n * 100, 2)}%'


def register_errorhandlers(app):
  def render_error(e="generic"):
    try:
      return render_template("errors/%s.html" % e.code), e.code
    except:
      try:
        return render_template("errors/%s.html" % e), e
      except:
        return render_template(f"errors/{requests.codes.INTERNAL_SERVER_ERROR}.html"), requests.codes.INTERNAL_SERVER_ERROR

  for e in [
    requests.codes.INTERNAL_SERVER_ERROR,
    requests.codes.NOT_FOUND,
    requests.codes.UNAUTHORIZED
  ]:
    app.errorhandler(e)(render_error)

  app.register_error_handler(HTTPException, render_error)

  def handle_db_exceptions(err):
    logger.error(f'Caught SQLAlchemy Error: {err}')
    try:
      logger.error('Rolling back session...')
      db.session.rollback()
    except Exception as rollback_err:
      logger.error(f'Exception rolling back session: {rollback_err}')
    try:
      logger.error('Closing session...')
      db.session.close()
    except Exception as close_err:
      logger.error(f'Exception closing session: {close_err}')
    return render_error(requests.codes.INTERNAL_SERVER_ERROR)

  app.register_error_handler(exc.SQLAlchemyError, handle_db_exceptions)


def register_request_handlers(app):

  # Redirect all URLs that point to this application to the host value in MODULE_SITE_HOST
  # Individual API calls may fail if request body not copied over(?), but these should only be sent
  # after initial page load, which will redirect to the correct host first
  @app.before_request
  def handle_redirects():
    if request.host != MODULE_SITE_HOST:
      return redirect(request.scheme + "://" + MODULE_SITE_HOST + request.full_path, code=301)


def password_protect_site(app):

  # Check the environment to determine whether the site should be password protected
  should_password_protect = get_env_var('MODULE_SITE_PASSWORD_PROTECTED', var_type=bool, can_be_none=True)
  if not should_password_protect:
    logger.debug(f'[SITE-PASSWORD] Not setting password for site (env = "{get_env_var("ENV")}", host = "{get_env_var("MODULE_SITE_HOST")}")')
    return

  # Create mapping of usernames to password environment variables
  # Env vars should hold the name of a secret, in turn containing the password for this account
  profiles = {
    'SITE_BASICAUTH_MTI_USERNAME':  'SITE_BASICAUTH_MTI_PASSWORD',
    'SITE_BASICAUTH_TEST_USERNAME': 'SITE_BASICAUTH_TEST_PASSWORD',
  }

  # Create the set of user accounts, skipping any for which the password can't be retrieved
  USERS = {}
  for username_secret, password_secret in profiles.items():
    try:
      USERS[get_secret(username_secret)] = generate_password_hash(get_secret(password_secret))
    except Exception as ex:
      logger.error(f'[SITE-PASSWORD] Could not create password-protected account for "{username_secret}": {ex}')

  # If no user accounts could be created, raise an error
  if len(USERS) == 0:
    msg = 'Could not password-protect site: no valid accounts.'
    logger.error(f'[SITE-PASSWORD] {msg}')
    raise BasicAuthError(msg)

  # Initialize basic auth object
  auth = HTTPBasicAuth()
  @auth.verify_password
  def verify_password(username, password):
    if username in USERS and check_password_hash(USERS.get(username), password):
      return username


  # Adapted from https://stackoverflow.com/a/30761573

  # A dummy callable to execute the login_required logic
  login_required_dummy_view = auth.login_required(lambda: None)

  @app.before_request
  def default_login_required():
    # Exclude 404 errors and static routes
    # Uses split to handle blueprint static routes as well
    if not request.endpoint or request.endpoint.rsplit('.', 1)[-1] == 'static':
      return

    return login_required_dummy_view()
