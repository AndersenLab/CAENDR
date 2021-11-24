
from flask import render_template, url_for, redirect, Blueprint
from caendr.utils.file import get_dir_list_sorted

primary_bp = Blueprint('primary', __name__)


@primary_bp.route('/')
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
def reroute_software():
  ''' This is a redirect due to a typo in the original CeNDR manuscript. Leave it. '''
  return redirect(url_for('primary.help_item', filename="Software"))


@primary_bp.route("/news")
@primary_bp.route("/news/<filename>/")
def news_item(filename=""):
  ''' News '''
  files = get_dir_list_sorted("static/content/news/")
  if not filename:
    filename = files[0].strip(".md")
  title = filename[11:].strip(".md").replace("-", " ")
  return render_template('news_item.html', **locals())


@primary_bp.route("/help")
@primary_bp.route("/help/<filename>/")
def help_item(filename=""):
  ''' Help '''
  # TODO: make files dynamic
  files = ["FAQ", "Variant-Browser", "Variant-Prediction", "Change-Log"]
  if not filename:
    filename = "FAQ"
  title = "Help"
  subtitle = filename.replace("-", " ")
  return render_template('primary/help.html', **locals())

'''
# TODO: Remove?

@primary_bp.route('/feed.atom')
def feed():
    """
        This view renders the sites ATOM feed.
    """
    fg = FeedGenerator()

    fg.id("CeNDR.News")
    fg.title("CeNDR News")
    fg.author({'name':'CeNDR Admin','email':'erik.andersen@northwestern.edu'})
    fg.link( href='http://example.com', rel='alternate' )
    fg.logo('http://ex.com/logo.jpg')
    fg.subtitle('This is a cool feed!')
    fg.language('en')
    fg.link( href=request.url, rel='self' )
    fg.language('en')
    files = get_dir_list_sorted("static/content/news/")  # files is a list of file names
    for filename in files:
        fe = fg.add_entry()
        fe.id(filename[11:].strip(".md").replace("-", " "))
        fe.title(filename[11:].strip(".md").replace("-", " "))
        fe.author({'name':'CeNDR Admin','email':'erik.andersen@northwestern.edu'})
        fe.link(href=urljoin(request.url_root, url_for("primary.news_item", filename=filename.strip(".md"))))
        fe.content(render_markdown(filename, "base/static/content/news/"))
        fe.pubDate(pytz.timezone("America/Chicago").localize(datetime.strptime(filename[:10], "%Y-%m-%d")))
    return fg.atom_str(pretty=True)
'''

@primary_bp.route('/outreach')
def outreach():
  title = "Outreach"
  
  # TODO: REPLACE THESE TEMPORARY ASSIGNMENTs
  protocol_url = 'https://storage.googleapis.com/elegansvariation.org/static/protocols/SamplingIsolationC.elegansNaturalHabitat.pdf'
  nematode_isolation_kit_form_url = 'http://docs.google.com/forms/d/15JXAQptqCSenZMyqHHOKQH1wJe7m0n8_Q0nHMe0eTUY/viewform?formkey=dERCQ1lsamU1ZFNtOGJJUkJqVzZOOVE6MQ#gid=0'
  
  return render_template('primary/outreach.html', **locals())


@primary_bp.route('/contact-us')
def contact():
  title = "Contact Us"
  return render_template('primary/contact.html', **locals())
