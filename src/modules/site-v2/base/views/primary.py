
from flask import render_template, url_for, redirect, Blueprint
from extensions import cache

from caendr.utils.file import get_dir_list_sorted
from caendr.api.strain import get_strains

primary_bp = Blueprint('primary', __name__)


@primary_bp.route('/')
@cache.memoize(60*60)
def primary():
  ''' Site home page '''

  try:
    strain_listing = [ strain.to_json() for strain in get_strains() ]
  except Exception:
    strain_listing = []

  # TODO: make news dynamic
  #files = sorted_files("base/static/content/news/")

  return render_template('primary/home.html', **{
    'page_title': 'Caenorhabditis elegans Natural Diversity Resource',
    #'files': files,
    'fluid_container': True,
    'strain_listing': strain_listing,
  })


@primary_bp.route("/Software")
@cache.memoize(60*60)
def reroute_software():
  ''' This is a redirect due to a typo in the original CeNDR manuscript. Leave it. '''
  return redirect(url_for('primary.help_item', filename="Software"))


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

