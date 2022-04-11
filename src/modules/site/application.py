import os
import json
import requests

from datetime import datetime
from logzero import logger
from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import HTTPException

from config import config
import pytz

from caendr.services.cloud.postgresql import health_database_status
from base.utils.markdown import render_markdown, render_ext_markdown

# --------- #
#  Routing  #
# --------- #
from base.views import primary_bp
from base.views import about_bp
from base.views import strains_bp
from base.views import user_bp
from base.views import order_bp
from base.views import mapping_bp

# Data
from base.views.data import data_bp
from base.views.data import releases_bp
from base.views.data import gene_browser_bp
from base.views.data import variant_browser_bp
from base.views.data import data_downloads_bp

# Tool
from base.views.tools import tools_bp
from base.views.tools import indel_primer_bp
from base.views.tools import heritability_bp

# API
from base.views.api import api_gene_bp

# Admin
from base.views.admin import admin_bp
from base.views.admin import admin_users_bp
from base.views.admin import admin_dataset_bp
from base.views.admin import admin_profile_bp
from base.views.admin import admin_tools_bp
from base.views.admin import admin_etl_op_bp
from base.views.admin import admin_gene_browser_tracks_bp
from base.views.admin import admin_content_bp

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
  jwt
)


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
  configure_jinja(app)
  configure_ssl(app)

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

def register_template_filters(app):
  for t_filter in [comma, format_release]:
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


def register_blueprints(app):
  """Register blueprints with the Flask application."""
  app.register_blueprint(primary_bp, url_prefix='')
  app.register_blueprint(about_bp, url_prefix='/about')
  app.register_blueprint(strains_bp, url_prefix='/strains')
  app.register_blueprint(order_bp, url_prefix='/order')

  # Data
  app.register_blueprint(data_bp, url_prefix='/data')
  app.register_blueprint(releases_bp, url_prefix='/data')
  app.register_blueprint(data_downloads_bp, url_prefix='/data')
  app.register_blueprint(gene_browser_bp, url_prefix='/data')
  app.register_blueprint(variant_browser_bp, url_prefix='/data')
  
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
  
  # Healthchecks/Maintenance
  app.register_blueprint(maintenance_bp, url_prefix='/tasks')
  app.register_blueprint(check_bp, url_prefix='')
  
  # API
  app.register_blueprint(api_gene_bp, url_prefix='/api')

  
  # Auth
  app.register_blueprint(auth_bp, url_prefix='/auth')
  app.register_blueprint(google_bp, url_prefix='/login')
  
  # Tools
  app.register_blueprint(mapping_bp, url_prefix='')
  app.register_blueprint(tools_bp, url_prefix='/tools')
  app.register_blueprint(indel_primer_bp, url_prefix='/tools')
  app.register_blueprint(heritability_bp, url_prefix='/tools')

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
      return aware_date.strftime('%Y-%m-%d %H:%M:%S %z')
    
  @app.template_filter('species_italic')
  def _jinja2_filter_species_italic(text):
    text = text.replace('C. briggsae', '<i>C. briggsae</i>')
    text = text.replace('C. elegans', '<i>C. elegans</i>')
    return text

def register_errorhandlers(app):
  def render_error(e="generic"):
    return render_template("errors/%s.html" % e.code), e.code

  for e in [
    requests.codes.INTERNAL_SERVER_ERROR,
    requests.codes.NOT_FOUND,
    requests.codes.UNAUTHORIZED
  ]:
    app.errorhandler(e)(render_error)

  app.register_error_handler(HTTPException, render_error)
