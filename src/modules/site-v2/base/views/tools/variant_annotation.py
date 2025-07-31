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
from caendr.models.datastore import Species, AnnotationFile
from caendr.models.error import NotFoundError
from caendr.models.sql import AnnovarAnnotatedVariant, CsqAnnotatedVariant, VepAnnotatedVariant, SnpEffAnnotatedVariant
from caendr.services.dataset_release import get_latest_dataset_release_version
from caendr.utils.bio import parse_chrom_interval, parse_chrom_position
from caendr.utils.constants import CHROM_INTERVAL_REGEX

# Load species list
annotation_tools = {
  "annovar": AnnovarAnnotatedVariant,
  "csq":     CsqAnnotatedVariant,
  "vep":     VepAnnotatedVariant,
  "snpeff":  SnpEffAnnotatedVariant,
}

variant_annotation_bp = Blueprint(
  'variant_annotation', __name__, template_folder='templates'
)



@variant_annotation_bp.route('')
@cache.memoize(60*60)
def variant_annotation():

  columns = {"": []}
  for name, tool in annotation_tools.items():
    tool_columns = tool.get_column_details()
    visibility_func = tool.column_default_visibility
    for col in tool_columns:
      col['default_visibility'] = visibility_func(col)
    columns[name] = tool_columns

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
    "columns": columns,

    # Data
    "strain_listing": strain_listing,
    "current_version": get_latest_dataset_release_version().version,
    "species_list": Species.all(),
    "annotation_list": AnnotationFile.all(),

    # List of Species class fields to expose to the template
    # Optional - exposes all attributes if not provided
    'species_fields': [
      'name', 'short_name', 'project_num', 'wb_ver', 'release_latest',
    ],

    # Misc
    "fluid_container": True,
    "chrom_interval_regex": CHROM_INTERVAL_REGEX,
  })



@variant_annotation_bp.route('/query/interval',                                          methods=['POST'])
@variant_annotation_bp.route('/query/interval/<string:tool_name>',                       methods=['POST'])
@variant_annotation_bp.route('/query/interval/<string:tool_name>/<string:species_name>', methods=['POST'])
@cache.memoize(60*60)
def query_interval(tool_name, species_name=None):
  if tool_name is not None and tool_name in annotation_tools:
    annotationtool = annotation_tools[tool_name]
  else:
    return abort(404)

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

  # Parse the query interval, returning an empty response if invalid
  try:
    interval = parse_chrom_interval(query)
  except ValueError as ex:
    logger.warn(ex)
    return jsonify({})

  # Run the query and return the results
  data = annotationtool.run_interval_query(interval, species=species)
  return jsonify(data)



@variant_annotation_bp.route('/query/position',                                          methods=['POST'])
@variant_annotation_bp.route('/query/position/<string:tool_name>',                       methods=['POST'])
@variant_annotation_bp.route('/query/position/<string:tool_name>/<string:species_name>', methods=['POST'])
@cache.memoize(60*60)
def query_position(tool_name, species_name=None):
  if tool_name is not None and tool_name in annotation_tools:
    annotationtool = annotation_tools[tool_name]
  else:
    return abort(404)

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

  # Parse the query position, returning an empty response if invalid
  try:
    position = parse_chrom_position(query)
  except ValueError as ex:
    logger.warn(ex)
    return jsonify({})

  # Run the query and return the results
  data = annotationtool.run_position_query(position, species=species)
  return jsonify(data)


@variant_annotation_bp.route('/download/csv/',                   methods=['POST'])
@variant_annotation_bp.route('/download/csv/<string:tool_name>', methods=['POST'])
def download_csv(tool_name):
  if tool_name is not None and tool_name in annotation_tools:
    annotationtool = annotation_tools[tool_name]
  else:
    return make_response(jsonify({ "message": "CSV download failed." }), 500)

  # Load columns from StrainAnnotatedVariant class
  columns = [ col['id'] for col in annotationtool.get_column_details() ]

  try:
    data = request.data
    pd_obj = pd.read_json(data)
    csv = pd_obj.to_csv(index=False, sep=",", columns=columns)

    res = make_response(csv)
    res.headers["Content-Disposition"] = f"attachment; filename={tool_name}_variant_annotation_data.csv"
    res.headers["Content-Type"] = "text/csv"
    return res

  except Exception as err:
    logger.error(err)
    return make_response(jsonify({ "message": "CSV download failed." }), 500)
