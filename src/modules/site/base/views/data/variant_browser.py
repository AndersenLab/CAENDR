from flask import (render_template,
                    Blueprint)

from caendr.api.isotype import get_isotypes


variant_browser_bp = Blueprint('variant_browser',
                        __name__,
                        template_folder='templates')


@variant_browser_bp.route('/vbrowser')
def vbrowser():
  title = 'Variant Annotation'
  alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.landing')}
  form = vbrowser_form()
  strain_listing = get_distinct_isotypes()
  columns = StrainAnnotatedVariants.column_details
  fluid_container = True
  return render_template('vbrowser.html', **locals())


@variant_browser_bp.route('/vbrowser/query/interval', methods=['POST'])
def vbrowser_query_interval():
  title = 'Variant Annotation'
  payload = json.loads(request.data)

  query = payload.get('query')

  is_valid = StrainAnnotatedVariants.verify_interval_query(q=query)
  if is_valid:
    data = StrainAnnotatedVariants.run_interval_query(q=query)
    return jsonify(data)

  return jsonify({})



@variant_browser_bp.route('/vbrowser/query/position', methods=['POST'])
def vbrowser_query_position():
  title = 'Variant Annotation'
  payload = json.loads(request.data)

  query = payload.get('query')

  is_valid = StrainAnnotatedVariants.verify_position_query(q=query)
  if is_valid:
    data = StrainAnnotatedVariants.run_position_query(q=query)
    return jsonify(data)

  return jsonify({})


