from flask import request, Blueprint
from logzero import logger

from caendr.api.gene import search_genes, search_homologs, get_gene
from caendr.utils.json import jsonify_request


api_gene_bp = Blueprint('api_gene',
                        __name__)


@api_gene_bp.route('/search/homologene/<string:query>')
@jsonify_request
def api_search_homologs(query=""):
  query = request.args.get('query') or query
  query = str(query).lower()
  return search_homologs(query)


@api_gene_bp.route('/search/gene/<string:query>')
@jsonify_request
def api_search_genes(query=""):
  query = request.args.get('query') or query
  query = str(query).lower()
  return search_genes(query)


@api_gene_bp.route('/search/<string:query>')
@jsonify_request
def api_search_combined(query=""):
  query = request.args.get('query') or query
  query = str(query).lower()
  return (search_genes(query) + search_homologs(query))[0:10]


@api_gene_bp.route('/search/interval/<string:gene>') # Seach for IGV Browser
@jsonify_request
def api_search_gene_interval(gene=None):
  if gene:
    result = get_gene(gene)
    if result:
      return {'result': [{"chromosome": result.chrom,
              'start': result.start,
              'end': result.end}]}
  return {'error': 'not found'}