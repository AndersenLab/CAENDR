from flask import ( render_template,
                    Blueprint,
                    jsonify,
                    url_for,
                    abort,
                  )

from caendr.services.logger import logger
from caendr.models.datastore import TraitFile


phenotype_db_bp = Blueprint(
  'phenotype_db', __name__, template_folder='templates'
)

@phenotype_db_bp.route('/table')
def get_table():
    """ Phenotype Database Traits Table """

    try:
      trait_files_list = TraitFile.query_ds()
    except Exception as ex:
       logger.error(f'Failed to retireve traits list: {ex}')
       abort(500)

    return render_template('tools/phenotype_db/table.html', **{
        
      # Page Info
      "title": 'Phenotype Database and Analysis',
      "tool_alt_parent_breadcrumb": { "title": "Tools", "url": url_for('tools.tools') },

      # Data
      "traits_listing": trait_files_list
    })

@phenotype_db_bp.route('/select')
def analysis_selection():
    pass
