import json

from flask import (render_template,
                    url_for,
                    request,
                    jsonify,
                    Blueprint)

from caendr.api.isotype import get_isotypes, get_distinct_isotypes
from caendr.models.sql import StrainAnnotatedVariant
from caendr.services.strain_annotated_variants import verify_interval_query, verify_position_query
from base.forms import VBrowserForm


variant_browser_bp = Blueprint('variant_browser',
                        __name__,
                        template_folder='templates')


@variant_browser_bp.route('/vbrowser')
def vbrowser():
  title = 'Variant Annotation'
  alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.landing')}
  form = VBrowserForm()
  strain_listing = get_distinct_isotypes()
  columns = StrainAnnotatedVariant.get_column_details()
  fluid_container = True
  return render_template('data/vbrowser.html', **locals())


@variant_browser_bp.route('/vbrowser/query/interval', methods=['POST'])
def vbrowser_query_interval():
  title = 'Variant Annotation'
  payload = json.loads(request.data)

  query = payload.get('query')

  is_valid = verify_interval_query(q=query)
  if is_valid:
    data = StrainAnnotatedVariant.run_interval_query(q=query)
    return jsonify(data)

  return jsonify({})



@variant_browser_bp.route('/vbrowser/query/position', methods=['POST'])
def vbrowser_query_position():
  title = 'Variant Annotation'
  payload = json.loads(request.data)

  query = payload.get('query')

  is_valid = verify_position_query(q=query)
  if is_valid:
    data = StrainAnnotatedVariant.run_position_query(q=query)
    return jsonify(data)

  return jsonify({})


