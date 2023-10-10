from flask import ( render_template,
                    Blueprint,
                    jsonify,
                    url_for,
                    abort,
                  )
from .phenotype_db_dicts import data_1
from .phenotype_db_dicts import data_2

import numpy as np
from scipy import stats
import scipy


phenotype_db_bp = Blueprint(
  'phenotype_db', __name__, template_folder='templates'
)

@phenotype_db_bp.route('/')
def phenotype_db():

  # Get the list of strains in both datasets by taking the intersection of their key sets
  # Convert back to a list because sets ~technically~ don't have a defined order -- we want to make sure
  # the list of strains is the same each time we use it
  overlap_strains = list( set(data_1.keys()).intersection(data_2.keys()) )

  # From each dataset, get a list of trait values for each strain in the overlapping set
  x = [ data_1[strain] for strain in overlap_strains ]
  y = [ data_2[strain] for strain in overlap_strains ]

  # Zip the trait values together with the strain names, to get the full dataset array
  data = list(zip(x, y, overlap_strains))

  # Compute the Spearman Coefficient for the given data
  res = stats.spearmanr(x, y)

  return render_template('tools/phenotype_db/phenotype.html', **{

    # Page info
    'title': f"Phenotype Database",
    'tool_alt_parent_breadcrumb': {
      "title": "Tools",
      "url": url_for('tools.tools')
    },

    # Data
    'data':        data,
    'correlation': res.correlation,
    'p_value':     res.pvalue,
  })