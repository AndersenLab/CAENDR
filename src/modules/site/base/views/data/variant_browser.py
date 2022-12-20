import json
from logzero import logger
import pandas as pd

from flask import (render_template,
                    url_for,
                    request,
                    redirect,
                    make_response,
                    jsonify,
                    flash,
                    Blueprint)
from extensions import cache
from base.forms import VBrowserForm

from caendr.api.isotype import get_isotypes, get_distinct_isotypes
from caendr.models.species import SPECIES_LIST
from caendr.models.sql import StrainAnnotatedVariant
from caendr.services.dataset_release import get_latest_dataset_release_version
from caendr.services.strain_annotated_variants import verify_interval_query, verify_position_query


variant_browser_bp = Blueprint('variant_browser',
                        __name__,
                        template_folder='templates')


@variant_browser_bp.route('/vbrowser')
@cache.memoize(60*60)
def vbrowser():

  # Load columns from StrainAnnotatedVariant class
  columns = StrainAnnotatedVariant.get_column_details()

  # Set function to decide which columns should be visible by default
  # Currently uses default values in class definition, but a different filter could be used if desired
  col_visibility_func = StrainAnnotatedVariant.column_default_visibility

  # Set whether columns should be visible by default as an object attribute
  for col in columns:
    col['default_visibility'] = col_visibility_func(col)

  # Create an options object to pass to vbrowser
  vbrowser_options = {

    # Page info
    "title": 'Variant Annotation',
    "alt_parent_breadcrumb": {
      "title": "Data",
      "url": url_for('data.landing')
    },
    "form": VBrowserForm(),

    # Data
    "strain_listing": get_distinct_isotypes(),
    "columns": columns,
    "current_version": get_latest_dataset_release_version().version,
    "species_list": SPECIES_LIST,

    # List of Species class fields to expose to the template
    # Optional - exposes all attributes if not provided
    'species_fields': [
      'name', 'short_name', 'project_num', 'wb_ver', 'latest_release',
    ],

    # Misc
    "fluid_container": True,
  }

  if request.args.get('download_err'):
    flash('CSV Download Failed.', 'error')
    return redirect(request.path)

  return render_template('data/vbrowser.html', **vbrowser_options)


@variant_browser_bp.route('/vbrowser/query/interval', methods=['POST'])
@cache.memoize(60*60)
def vbrowser_query_interval():
  title = 'Variant Annotation'
  payload = json.loads(request.data)

  query = payload.get('query')

  is_valid = verify_interval_query(query=query)
  if is_valid:
    data = StrainAnnotatedVariant.run_interval_query(query=query)
    return jsonify(data)

  return jsonify({})



@variant_browser_bp.route('/vbrowser/query/position', methods=['POST'])
@cache.memoize(60*60)
def vbrowser_query_position():
  title = 'Variant Annotation'
  payload = json.loads(request.data)

  query = payload.get('query')

  is_valid = verify_position_query(query=query)
  if is_valid:
    data = StrainAnnotatedVariant.run_position_query(query=query)
    return jsonify(data)

  return jsonify({})


@variant_browser_bp.route('/vbrowser/download/csv', methods=['POST'])
def vbrowser_download_csv():
  try:
    data = request.data
    pd_obj = pd.read_json(data)
    csv = pd_obj.to_csv(index=False, sep=",")
    res = make_response(csv)
    res.headers["Content-Disposition"] = "attachment; filename=data.csv"
    res.headers["Content-Type"] = "text/csv"
    return res
  except Exception as err:
    logger.error(err)
    return make_response(jsonify({ "message": "CSV download failed." }), 500)


