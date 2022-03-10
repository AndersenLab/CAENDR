import json
import pandas as pd

from flask import (render_template,
                    url_for,
                    request,
                    make_response,
                    jsonify,
                    flash,
                    Blueprint)
from extensions import cache
from base.forms import VBrowserForm

from caendr.api.isotype import get_isotypes, get_distinct_isotypes
from caendr.models.sql import StrainAnnotatedVariant
from caendr.services.strain_annotated_variants import verify_interval_query, verify_position_query


variant_browser_bp = Blueprint('variant_browser',
                        __name__,
                        template_folder='templates')


@variant_browser_bp.route('/vbrowser')
@cache.memoize(60*60)
def vbrowser():
  title = 'Variant Annotation'
  alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.landing')}
  form = VBrowserForm()
  strain_listing = get_distinct_isotypes()
  columns = StrainAnnotatedVariant.get_column_details()
  fluid_container = True
  return render_template('data/vbrowser.html', **locals())


@variant_browser_bp.route('/vbrowser/query/interval', methods=['POST'])
@cache.memoize(60*60)
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
@cache.memoize(60*60)
def vbrowser_query_position():
  title = 'Variant Annotation'
  payload = json.loads(request.data)

  query = payload.get('query')

  is_valid = verify_position_query(q=query)
  if is_valid:
    data = StrainAnnotatedVariant.run_position_query(q=query)
    return jsonify(data)

  return jsonify({})


@variant_browser_bp.route('/vbrowser/download/csv', methods=['POST'])
@cache.memoize(60*60)
def vbrowser_download_csv():
    data = request.data
    pd_obj = pd.read_json(data)

    csv = pd_obj.to_csv(index=False, sep=",")
    res = make_response(csv)
    res.headers["Content-Disposition"] = "attachment; filename=data.csv"
    res.headers["Content-Type"] = "text/csv"
    return res


