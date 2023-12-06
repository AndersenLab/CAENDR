import bleach
from flask import Response, Blueprint, render_template, request, url_for, jsonify, redirect, flash, abort

from base.forms              import PhenotypeComparisonForm
from base.utils.auth         import jwt_required, get_current_user, user_is_admin
from base.utils.tools        import try_submit

from caendr.models.datastore import Species, PhenotypeReport



phenotype_comparison_bp = Blueprint(
  'phenotype_comparison', __name__, template_folder='templates'
)



@phenotype_comparison_bp.route('/')
def phenotype_comparison():

  # Construct variables and render template
  return render_template('tools/phenotype/submit.html', **{

    # Page info
    "title": "Phenotype Comparison",
    "form":  PhenotypeComparisonForm(request.form),
    "tool_alt_parent_breadcrumb": {
      "title": "Tools",
      "url":   url_for('tools.tools')
    },

    # List of Species class fields to expose to the template
    "species_list": Species.all(),
    'species_fields': [
      'name', 'short_name', 'project_num', 'wb_ver', 'release_latest',
    ],

    # String replacement tokens
    # Maps token to the field in Species object it should be replaced with
    'tokens': {
      'WB':      'wb_ver',
      'RELEASE': 'release_latest',
      'PRJ':     'project_num',
      'GENOME':  'fasta_genome',
    },

    # Misc
    "fluid_container": True,
  })



@phenotype_comparison_bp.route('/submit', methods=["POST"])
@jwt_required()
def submit():
  form = PhenotypeComparisonForm(request.form)
  user = get_current_user()

  # Validate form fields
  # Checks that species is in species list & label is not empty
  if not form.validate_on_submit():
    msg = "Invalid submission"
    flash(msg, "danger")
    return jsonify({ 'message': msg }), 400

  # Read fields from form
  data = {
    field: bleach.clean(request.form.get(field))
      for field in {'label', 'species', 'trait_1', 'trait_2'}
  }

  # If user is admin, allow them to bypass cache with URL variable
  no_cache = bool(user_is_admin() and request.args.get("nocache", False))

  # Try submitting the job & getting a JSON status message
  response, code = try_submit(PhenotypeReport.kind, user, data, no_cache)

  # If there was an error, flash it
  if code != 200 and int(request.args.get('reloadonerror', 1)):
    flash(response['message'], 'danger')

  # Return the response
  return jsonify( response ), code
