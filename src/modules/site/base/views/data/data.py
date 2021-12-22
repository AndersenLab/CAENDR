from flask import render_template, Blueprint
from extensions import cache

data_bp = Blueprint('data',
                    __name__,
                    template_folder='templates')


@data_bp.route('/')
@cache.memoize(60*60)
def landing():
  disable_parent_breadcrumb = True
  return render_template('data/landing.html', **locals())

