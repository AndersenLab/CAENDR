from flask import ( render_template,
                    Blueprint,
                    jsonify,
                    url_for,
                    abort,
                  )


phenotype_db_bp = Blueprint(
  'phenotype_db', __name__, template_folder='templates'
)


