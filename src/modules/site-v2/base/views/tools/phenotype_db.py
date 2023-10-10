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

  x_arr = []
  y_arr = []
  data_dict = {}
  data_arr = []
  for s in overlap_strains:
    x_arr.append(data_1[s])
    y_arr.append(data_2[s])
    data_dict[s] = [data_1[s], data_2[s]]
    data_arr.append([data_1[s], data_2[s], s])
  x = np.array(x_arr)
  y = np.array(y_arr)
  res = stats.spearmanr(x, y)
  c = res.correlation
  p_value = res.pvalue
  return render_template('tools/phenotype_db/phenotype.html', **{

    # Page info
    'title': f"Phenotype Database",
    'tool_alt_parent_breadcrumb': {
      "title": "Tools",
      "url": url_for('tools.tools')
    },

    # Data
    'paraquat': x_arr,
    'carbaryl': y_arr,
    'data_dict': data_dict,
    'data_arr': data_arr,
    'correlation': c,
    'p_value': p_value
  })