import json
from caendr.services.logger import logger
import pandas as pd

from flask import (render_template,
                    url_for,
                    request,
                    redirect,
                    make_response,
                    jsonify,
                    flash,
                    abort,
                    Blueprint)
from extensions import cache
from base.forms import VBrowserForm

from caendr.api.isotype import get_distinct_isotypes
from caendr.models.datastore import Species
from caendr.models.error import NotFoundError
from caendr.models.sql import StrainAnnotatedVariant
from caendr.services.dataset_release import get_latest_dataset_release_version
from caendr.services.strain_annotated_variants import verify_interval_query, verify_position_query


variant_annotation_bp = Blueprint(
  'variant_annotation', __name__, template_folder='templates'
)



@variant_annotation_bp.route('')
@cache.memoize(60*60)
def variant_annotation():

  # Load columns from StrainAnnotatedVariant class
  columns = StrainAnnotatedVariant.get_column_details()

  # Set function to decide which columns should be visible by default
  # Currently uses default values in class definition, but a different filter could be used if desired
  col_visibility_func = StrainAnnotatedVariant.column_default_visibility

  # Set whether columns should be visible by default as an object attribute
  for col in columns:
    col['default_visibility'] = col_visibility_func(col)

  # Organize distinct isotypes by species
  strain_listing = { name: sorted( get_distinct_isotypes(species=name) ) for name in Species.all() }

  if request.args.get('download_err'):
    flash('CSV Download Failed.', 'error')
    return redirect(request.path)

  # Render the page
  return render_template('tools/variant_annotation/vbrowser.html', **{

    # Page info
    "title": 'Variant Annotation',
    "tool_alt_parent_breadcrumb": { "title": "Tools", "url": url_for('tools.tools') },
    "form": VBrowserForm(),

    # Data
    "strain_listing": strain_listing,
    "columns": columns,
    "current_version": get_latest_dataset_release_version().version,
    "species_list": Species.all(),

    # List of Species class fields to expose to the template
    # Optional - exposes all attributes if not provided
    'species_fields': [
      'name', 'short_name', 'project_num', 'wb_ver', 'release_latest',
    ],

    # Misc
    "fluid_container": True,
  })



@variant_annotation_bp.route('/query/interval',                       methods=['POST'])
@variant_annotation_bp.route('/query/interval/<string:species_name>', methods=['POST'])
@cache.memoize(60*60)
def query_interval(species_name=None):

  # Extract the query
  payload = json.loads(request.data)
  query = payload.get('query')

  # Get the species from the URL, allowing undefined
  if species_name:
    try:
      species = Species.from_name(species_name, from_url=True)
    except NotFoundError:
      return abort(404)
  else:
    species = None

  # If query is valid, run it and return the results
  is_valid = verify_interval_query(query=query)
  if is_valid:
    data = StrainAnnotatedVariant.run_interval_query(query=query, species=species)
    return jsonify(data)

  # Otherwise, return an empty response
  return jsonify({})



@variant_annotation_bp.route('/query/position',                       methods=['POST'])
@variant_annotation_bp.route('/query/position/<string:species_name>', methods=['POST'])
@cache.memoize(60*60)
def query_position(species_name=None):

  # Extract the query
  payload = json.loads(request.data)
  query = payload.get('query')

  # Get the species from the URL, allowing undefined
  if species_name:
    try:
      species = Species.from_name(species_name, from_url=True)
    except NotFoundError:
      return abort(404)
  else:
    species = None

  # If query is valid, run it and return the results
  is_valid = verify_position_query(query=query)
  if is_valid:
    data = StrainAnnotatedVariant.run_position_query(query=query, species=species)
    return jsonify(data)

  # Otherwise, return an empty response
  return jsonify({})



@variant_annotation_bp.route('/download/csv', methods=['POST'])
def download_csv():

  # Load columns from StrainAnnotatedVariant class
  columns = [ col['id'] for col in StrainAnnotatedVariant.get_column_details() ]

  try:
    data = request.data
    pd_obj = pd.read_json(data)
    csv = pd_obj.to_csv(index=False, sep=",", columns=columns)

    res = make_response(csv)
    res.headers["Content-Disposition"] = "attachment; filename=variant_annotation_data.csv"
    res.headers["Content-Type"] = "text/csv"
    return res

  except Exception as err:
    logger.error(err)
    return make_response(jsonify({ "message": "CSV download failed." }), 500)
