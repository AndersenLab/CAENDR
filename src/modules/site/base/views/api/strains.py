from caendr.services.logger import logger
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from caendr.models.datastore      import Species
from caendr.services.indel_primer import get_sv_strains as get_sv_strains_helper



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
