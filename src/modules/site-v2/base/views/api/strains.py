from caendr.services.logger import logger
from flask import Blueprint, jsonify

from base.utils.auth import jwt_required, admin_required, get_current_user, user_is_admin

from caendr.models.datastore             import Species
from caendr.services.guide_rna_selection import get_grna_selection_strains as get_grna_selection_strains_helper
from caendr.services.indel_primer        import get_sv_strains             as get_sv_strains_helper



api_strains_bp = Blueprint(
  'api_strains', __name__
)



#
# Endpoints
#


@api_strains_bp.route('/sv', methods=['GET'])
@jwt_required()
def get_sv_strains():

  # Helper function to try getting the strain list for a species and print an error message if not available
  def try_get_sv_strains(species):
    try:
      return get_sv_strains_helper(species)
    except Exception as e:
      logger.error(f"Couldn't find strain variant annotations for {species}. Make sure the appropriate VCF file exists. Full error: {e}")
      return []

  # Return the strains for each species
  return jsonify({
    species: try_get_sv_strains( species ) for species in Species.all().keys()
  })


@api_strains_bp.route('/grna-selection', methods=['GET'])
@jwt_required()
def get_grna_selection_strains():

  # Helper function to try getting the strain list for a species and print an error message if not available
  def try_get_grna_selection_strains(species):
    try:
      return get_grna_selection_strains_helper(species)
    except Exception as e:
      logger.error(f"Couldn't find gRNA selection strains for {species}. Full error: {e}")
      return []

  # Return the strains for each species
  return jsonify({
    species: try_get_grna_selection_strains( species ) for species in Species.all().keys()
  })
