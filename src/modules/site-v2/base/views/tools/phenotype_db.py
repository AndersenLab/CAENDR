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
  pass