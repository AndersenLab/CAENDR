from flask import (render_template,
                    Blueprint)


# Tools blueprint
tools_bp = Blueprint('tools',
                      __name__,
                      template_folder='templates')


@tools_bp.route('/')
def tools():
  disable_parent_breadcrumb = False
  return render_template('tools/tools.html', **locals())

