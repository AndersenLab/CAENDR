from flask import render_template, abort, Blueprint, redirect, url_for

from caendr.api.phenotype   import get_trait_categories

from caendr.services.logger import logger
from caendr.utils.env       import get_env_var

from base.forms             import EmptyForm
from base.utils.auth        import admin_required



admin_traits_bp = Blueprint(
  'admin_traits', __name__
)



#
# Endpoints
#


@admin_traits_bp.route('/', methods=['GET'])
@admin_required()
def admin_traits():
  '''
    Default endpoint for this blueprint.
    Redirect to the trait queue.
  '''
  return redirect(url_for(f'{ admin_traits_bp.name }.trait_queue'))


@admin_traits_bp.route('/queue', methods=['GET'])
@admin_required()
def trait_queue():
  '''
    List the traits that have been submitted for review to enter the public Phenotype Database.
  '''

  # Get the list of unique tags
  try:
    categories = get_trait_categories()

  except Exception as ex:
    logger.error(f'Failed to retrieve the list of traits: {ex}')
    abort(500, description='Failed to retrieve the list of traits')

  return render_template('admin/traits/submission-queue.html', **{
    # Page info
    'title': 'Trait Submission Queue',
    'tool_alt_parent_breadcrumb': {"title": "Admin", "url": url_for('admin.admin')},

    # Data
    'categories': categories,
    'form': EmptyForm(),
  })
