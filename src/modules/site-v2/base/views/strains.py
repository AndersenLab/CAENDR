from caendr.services.logger import logger
from flask import (render_template,
                   request,
                   url_for,
                   redirect,
                   Response,
                   Blueprint,
                   abort,
                   flash,
                   Markup,
                   stream_with_context)

from config import config
from extensions import cache

from caendr.api.strain import get_strains, query_strains, get_strain_sets, get_strain_img_url
from caendr.models.sql import Strain
from caendr.utils.json import dump_json


strains_bp = Blueprint('strains',
                        __name__,
                        template_folder='templates')
#
# Strain List Page
#
@strains_bp.route('/')
@cache.memoize(60*60)
def strains():
  """ Redirect base route to the strain list page """
  disable_parent_breadcrumb = True
  return render_template('strain/strains.html', **locals())

@strains_bp.route('/map')
@cache.memoize(60*60)
def strains_map():
  """ Redirect base route to the strain list page """
  title = 'Strain Map'
  strains = get_strains()
  strain_listing = [s.to_json() for s in strains]
  return render_template('strain/map.html', **locals())

@strains_bp.route('/isotype_list')
@cache.memoize(60*60)
def strains_list():
  """ Strain list of all wild isolates within the SQL database and a table of all strains """
  VARS = {'title': 'Isotype List',
          'strain_listing': get_strains()}
  return render_template('strain/list.html', **VARS)

@strains_bp.route('/issues')
@cache.memoize(60*60)
def strains_issues():
  """ Strain issues shows latest data releases table of strain issues """
  VARS = {'title': 'Strain Issues',
          'strain_listing_issues': get_strains(issues=True)}
  return render_template('strain/issues.html', **VARS)


@strains_bp.route('/external-links')
@cache.memoize(60*60)
def external_links():
  """ Shows external website links """
  title = 'External Links'
  return render_template('strain/external_links.html', **locals())


#
# Strain Data
#
@strains_bp.route('/CelegansStrainData.tsv')
@cache.memoize(60*60)
def strains_data_tsv():
  """
      Dumps strain dataset; Normalizes lat/lon on the way out.
  """

  def generate():
    col_list = list(Strain.__mapper__.columns)
    col_order = [1, 0, 3, 4, 5, 7, 8, 9, 10, 28, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 2, 6]
    col_list[:] = [col_list[i] for i in col_order]
    header = [x.name for x in col_list]
    yield '\t'.join(header) + "\n"
    for row in query_strains(issues=False):
      row = [getattr(row, column.name) for column in col_list]
      yield '\t'.join(map(str, row)) + "\n"

  return Response(stream_with_context(generate()), mimetype="text/tab-separated-values")


#
# Isotype View
#
@strains_bp.route('/isotype/<isotype_name>/')
@strains_bp.route('/isotype/<isotype_name>/<release>')
@cache.memoize(60*60)
def isotype_page(isotype_name, release=None):
  """ Isotype page """
  isotype_strains = query_strains(isotype_name=isotype_name)
  if not isotype_strains:
    abort(404)

  # Fetch isotype images
  image_urls = {}
  for s in isotype_strains:
    image_urls[s.strain] = {'url': get_strain_img_url(s.strain),
                            'thumb': get_strain_img_url(s.strain, thumbnail=True)}

  logger.debug(image_urls)
  VARS = {"title": f"Isotype {isotype_name}",
          "isotype": isotype_strains,
          "isotype_name": isotype_name,
          "isotype_ref_strain": [x for x in isotype_strains if x.isotype_ref_strain][0],
          "strain_json_output": dump_json(isotype_strains),
          "image_urls": image_urls}
  return render_template('strain/isotype.html', **VARS)


#
# Strain Catalog
#

@strains_bp.route('/catalog', methods=['GET', 'POST'])
@cache.memoize(60*60)
def strains_catalog():
    flash(Markup("Strain mapping sets 9 and 10 will not be available until later this year."), category="warning")
    title = "Strain Catalog"
    warning = request.args.get('warning')
    strain_listing = get_strains()
    strain_sets = get_strain_sets()
    return render_template('strain/catalog.html', **locals())
