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

@phenotype_database_bp.route('/report/')
def report():
  return render_template('tools/phenotype_database/report.html', **{
    # Page info
    'title': 'Phenotype Analysis Report',
    'tool_alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},
  })

@phenotype_database_bp.route('/analysis/stepA')
def analysisA():
  return render_template('tools/phenotype_database/phenotypeAnalysisA.html', **{
    # Page info
    'title': 'Phenotype Analysis',
    'tool_alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},
  })

@phenotype_database_bp.route('/analysis/stepB')
def analysisB():
  return render_template('tools/phenotype_database/phenotypeAnalysisB.html', **{
    # Page info
    'title': 'Phenotype Analysis',
    'tool_alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},
  })

@phenotype_database_bp.route('/analysis/stepC')
def analysisC():
  return render_template('tools/phenotype_database/phenotypeAnalysisC.html', **{
    # Page info
    'title': 'Phenotype Analysis',
    'tool_alt_parent_breadcrumb': {"title": "Tools", "url": url_for('tools.tools')},
  })