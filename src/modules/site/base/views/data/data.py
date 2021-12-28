from flask import render_template, Blueprint


data_bp = Blueprint('data',
                    __name__,
                    template_folder='templates')


@data_bp.route('/')
def landing():
  disable_parent_breadcrumb = True
  return render_template('data/landing.html', **locals())

