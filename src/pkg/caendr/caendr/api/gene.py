from flask import request, Blueprint
from caendr.models.sql import Homolog, WormbaseGeneSummary
from sqlalchemy import or_, func
from caendr.services.logger import logger


def get_gene(query: str):
  """Lookup a single gene

    Lookup gene in the wormbase summary gene table.

    Args:
        query (str): Query string

    Returns:
        result (dict): List of dictionaries describing the homolog.
  """
  query = request.args.get('query') or query
  query = str(query).lower()
  # First identify exact match
  result = WormbaseGeneSummary.query.filter(or_(func.lower(WormbaseGeneSummary.locus) == query,
                                                func.lower(WormbaseGeneSummary.sequence_name) == query,
                                                func.lower(WormbaseGeneSummary.gene_id) == query)) \
                                              .first()
  if not result:
      result = WormbaseGeneSummary.query.filter(or_(func.lower(WormbaseGeneSummary.locus).startswith(query),
                                                    func.lower(WormbaseGeneSummary.sequence_name).startswith(query),
                                                    func.lower(WormbaseGeneSummary.gene_id).startswith(query))) \
                                                  .first()
  return result


def search_genes(query: str):
  """Query gene

  Query genes in the wormbase summary gene table.

  Args:
      query (str): Query string

  Returns:
      results (list): List of dictionaries with gene results.
  """
  results = WormbaseGeneSummary.query.filter(or_(func.lower(WormbaseGeneSummary.locus).startswith(query),
                                                  func.lower(WormbaseGeneSummary.sequence_name).startswith(query),
                                                  func.lower(WormbaseGeneSummary.gene_id).startswith(query))) \
                                            .limit(10) \
                                            .all()

  results = [x.to_json() for x in results]
  return results


def search_homologs(query: str):
  """Query homolog

  Query the homologs database and return C. elegans homologs.

  Args:
      query (str): Query string

  Returns:
      results (list): List of dictionaries describing the homolog.

  """
  query = request.args.get('query') or query
  query = query.lower()
  results = Homolog.query.filter((func.lower(Homolog.homolog_gene)).startswith(query)) \
                            .limit(10) \
                            .all()
  results = [x.unnest().to_json() for x in results]
  return results



def combined_search(query: str):
  """Combines homolog and gene searches
  
  Args:
      query (str): Query string

  Returns:
      results (list): List of dictionaries describing the homolog.
  """
  return (search_genes(query) + search_homologs(query))[0:10]


def gene_variants(query: str):
  """Return a list of variants within a gene.

  Args:
      query: gene name or ID

  Returns:
      results (list): List of variants within a gene
  """

  gene_record = get_gene(query)
  gene_variants = variant_query(gene_record.interval)
  #for row in gene_variants:
      # Filter ANN for annotations for gene
  #    row['ANN'] = [x for x in row['ANN'] if gene_record.gene_id == x['gene_id']]
  return gene_variants

  
  
def search_interval(gene: str):
  result = get_gene(gene)
  if result:
    return {'result': 
            [
              {"chromosome": result.chrom,
              'start': result.start,
              'end': result.end}
              ]
            }
  else:
    return {'error': 'not found'}