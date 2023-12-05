import json
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


phenotype_database_bp = Blueprint(
  'phenotype_database', __name__, template_folder='templates'
)

@phenotype_database_bp.route('')
@cache.memoize(60*60)
def phenotype_database():
  return render_template('tools/phenotype_database/phenotypedb.html', **{
    # Page info
    "title": 'Phenotype Database and Analysis',
    "tool_alt_parent_breadcrumb": { "title": "Tools", "url": url_for('tools.tools') },
  })