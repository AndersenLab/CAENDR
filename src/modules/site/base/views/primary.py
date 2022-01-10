
from flask import render_template, url_for, redirect, Blueprint
from extensions import cache

from caendr.utils.file import get_dir_list_sorted

primary_bp = Blueprint('primary', __name__)


@primary_bp.route('/')
@cache.memoize(60*60)
def primary():
  ''' Site home page '''
  page_title = "Caenorhabditis elegans Natural Diversity Resource"
  # TODO: make news dynamic
  #files = sorted_files("base/static/content/news/")
  VARS = {
    'page_title': page_title,
    #'files': files,
    'fluid_container': True 
  }
  return render_template('primary/home.html', **VARS)


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
  files = get_dir_list_sorted("static/content/news/")
  if not filename:
    filename = files[0].strip(".md")
  title = filename[11:].strip(".md").replace("-", " ")
  return render_template('news_item.html', **locals())


@primary_bp.route("/help")
@primary_bp.route("/help/<filename>/")
@cache.memoize(60*60)
def help_item(filename=""):
  ''' Help '''
  # TODO: make files dynamic
  files = ["FAQ", "Variant-Browser", "Change-Log"]
  if not filename:
    filename = "FAQ"
  title = "Help"
  subtitle = filename.replace("-", " ")
  return render_template('primary/help.html', **locals())


@primary_bp.route('/outreach')
@cache.memoize(60*60)
def outreach():
  title = "Outreach"
  
  # TODO: REPLACE THESE TEMPORARY ASSIGNMENTs
  protocol_url = 'https://storage.googleapis.com/elegansvariation.org/static/protocols/SamplingIsolationC.elegansNaturalHabitat.pdf'
  nematode_isolation_kit_form_url = 'http://docs.google.com/forms/d/15JXAQptqCSenZMyqHHOKQH1wJe7m0n8_Q0nHMe0eTUY/viewform?formkey=dERCQ1lsamU1ZFNtOGJJUkJqVzZOOVE6MQ#gid=0'
  
  return render_template('primary/outreach.html', **locals())


@primary_bp.route('/contact-us')
@cache.memoize(60*60)
def contact():
  title = "Contact Us"
  return render_template('primary/contact.html', **locals())

