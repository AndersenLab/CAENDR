import os
from flask import render_template, url_for, redirect, Blueprint, jsonify, flash, Markup
from extensions import cache, compress

from caendr.utils.file import get_dir_list_sorted
from caendr.api.strain import get_strains

primary_bp = Blueprint('primary', __name__)


@primary_bp.route('/')
@cache.memoize(60*60)
def primary():
  ''' Site home page '''

  # TODO: make news dynamic
  #files = sorted_files("base/static/content/news/")

  flash(Markup("Welcome to the beta release of CaeNDR!"), category="success")

  return render_template('primary/home.html', **{
    'page_title': 'Caenorhabditis elegans Natural Diversity Resource',
    #'files': files,
    'fluid_container': True,
  })

@primary_bp.route('/version')
@cache.memoize(60*60)
def version():
  version = os.environ.get("MODULE_VERSION", "n/a")
  git_commit = os.environ.get("GIT_COMMIT", "n/a")
  return jsonify({
    'version': version,
    'git_commit': git_commit
  })


@primary_bp.route('/strains')
@cache.memoize(60*60*24)
@compress.compressed()
def get_strains_json():
  try:
    strain_listing = [ strain.to_json() for strain in get_strains() ]
  except Exception:
    strain_listing = []
  return jsonify(strain_listing)


@primary_bp.route("/Software")
@cache.memoize(60*60)
def reroute_software():
  ''' This is a redirect due to a typo in the original CeNDR manuscript. Leave it. '''
  return redirect(url_for('primary.help_item', filename="Software"))


@primary_bp.route("/strains/isotype_list")
def reroute_isotype_list():
  '''
    This is a redirect for older Genome Mapping reports, which use an older version of this URL.
  '''
  return redirect(url_for('request_strains.strains_list'))



@primary_bp.route("/news")
@primary_bp.route("/news/<filename>/")
@cache.memoize(60*60)
def news_item(filename=""):
  ''' News '''
  files = get_dir_list_sorted("base/static/content/news/")
  if not filename:
    filename = files[0].strip(".md")
  title = filename[11:].strip(".md").replace("-", " ")
  return render_template('news/news_item.html', **locals())


@primary_bp.route("/faq")
@primary_bp.route("/faq/<filename>/")
@cache.memoize(60*60)
def help_item(filename=""):
  ''' Help '''
  # TODO: make files dynamic
  files = ["FAQ"]
  if not filename:
    filename = "FAQ"
  title = "FAQ"
  return render_template('faq/faq.html', **locals())

