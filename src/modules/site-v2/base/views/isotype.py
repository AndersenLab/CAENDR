from caendr.services.logger import logger

from extensions import cache, compress
from flask import render_template, request, url_for, redirect, Blueprint, abort, flash, jsonify

from caendr.api.strain import query_strains, get_strain_img_url
from caendr.utils.json import dump_json



isotype_bp = Blueprint(
  'isotype', __name__, template_folder='templates'
)



#
# Base View
#

@isotype_bp.route('/')
@cache.memoize(60*60)
def isotype():
  """
    Required root endpoint.
  """
  abort(404)



#
# Isotype View
#

@isotype_bp.route('/<isotype_name>/')
@isotype_bp.route('/<isotype_name>/<release>')
@cache.memoize(60*60)
def isotype_page(isotype_name, release=None):
  """
    Isotype page
  """

  isotype_strains = query_strains(isotype_name=isotype_name)
  if not isotype_strains:
    abort(404)

  return render_template('strain/isotype.html', **{
    "title": f"Isotype {isotype_name}",
    "isotype": isotype_strains,
    "isotype_name": isotype_name,
    "isotype_ref_strain": [ x for x in isotype_strains if x.isotype_ref_strain ][0],
    "strain_json_output": dump_json(isotype_strains)
  })



#
# Isotype image URLs
#

@isotype_bp.route('/img/<isotype_name>/')
@cache.memoize(60*60)
def isotype_img(isotype_name, release=None):
  """
    Fetching isotype images
  """

  isotype_strains = query_strains(isotype_name=isotype_name)
  if not isotype_strains:
    abort(404)

  image_urls = {}
  for s in isotype_strains:
    image_urls[s.strain] = {
      'url':   get_strain_img_url(s.strain, species=s.species_name, thumbnail=False),
      'thumb': get_strain_img_url(s.strain, species=s.species_name, thumbnail=True),
    }

  logger.debug(image_urls)
  return jsonify(image_urls)

