from flask import request, Blueprint
from caendr.services.logger import logger
from extensions import cache

from caendr.api.gene import search_genes, search_homologs, get_gene, remove_prefix
from caendr.utils.json import jsonify_request
from caendr.models.datastore import SPECIES_LIST


api_gene_bp = Blueprint('api_gene',
                        __name__)


# @api_gene_bp.route('/search/homologene/<string:query>')
# @cache.memoize(60*60)
# @jsonify_request
# def api_search_homologs(query=""):
#   query = request.args.get('query') or query
#   query = str(query).lower()
#   species = request.args.get('species') or None
#   return search_homologs(query, species=species)


@api_gene_bp.route('/search/gene/<string:query>')
@cache.memoize(60*60)
@jsonify_request
def api_search_genes(query=""):
  query = request.args.get('query', query)
  query = str(query).lower()
  species = request.args.get('species')

  # If a species was provided, remove the optional species-specific gene prefix from the query
  if species:
    species_object = SPECIES_LIST[species]
    query = remove_prefix(query, species_object['gene_prefix'].lower())

  return search_genes(query, species=species)


# @api_gene_bp.route('/search/<string:query>')
# @cache.memoize(60*60)
# @jsonify_request
# def api_search_combined(query=""):
#   query = request.args.get('query') or query
#   query = str(query).lower()
#   species = request.args.get('species') or None
#   return (search_genes(query, species=species) + search_homologs(query, species=species))[0:10]


@api_gene_bp.route('/search/interval/<string:gene>') # Seach for IGV Browser
@cache.memoize(60*60)
@jsonify_request
def api_search_gene_interval(gene=None):
  if gene:
    result = get_gene(gene)
    if result:
      return {'result': [{"chromosome": result.chrom,
              'start': result.start,
              'end': result.end}]}
  return {'error': 'not found'}