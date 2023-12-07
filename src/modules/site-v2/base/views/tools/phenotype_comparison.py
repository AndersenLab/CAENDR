from flask import Response, Blueprint, render_template, request, url_for, jsonify, redirect, flash, abort

from base.forms              import PhenotypeComparisonForm

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
