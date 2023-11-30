from flask import ( render_template,
                    Blueprint,
                    jsonify,
                    url_for,
                    abort,
                  )


phenotype_db_bp = Blueprint(
  'phenotype_db', __name__, template_folder='templates'
)

@phenotype_db_bp.route('/table')
def get_table():
    return render_template('tools/phenotype_db/table.html', **{
      "title": 'Phenotype Database',
      "tool_alt_parent_breadcrumb": { "title": "Tools", "url": url_for('tools.tools') },
    })
