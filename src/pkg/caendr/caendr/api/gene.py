from flask import request, Blueprint
from caendr.models.sql import Homolog, WormbaseGeneSummary

from sqlalchemy import and_, or_, func
from caendr.services.logger import logger


def get_gene(query: str):
  """Lookup a single gene

    Lookup gene in the wormbase summary gene table.

    Args:
        query (str): Query string

    Returns:
        result (dict): List of dictionaries describing the homolog.
  """

  # Extract query value from request or function argument
  query = request.args.get('query', query).lower()

  # First identify exact match
  result = WormbaseGeneSummary.query.filter(
    or_(
      func.lower(WormbaseGeneSummary.locus)         == query,
      func.lower(WormbaseGeneSummary.sequence_name) == query,
      func.lower(WormbaseGeneSummary.gene_id)       == query
    )
  ).first()

  # If no exact match found, search for gene that starts with query
  if not result:
    result = WormbaseGeneSummary.query.filter(
      or_(
        func.lower(WormbaseGeneSummary.locus).startswith(query),
        func.lower(WormbaseGeneSummary.sequence_name).startswith(query),
        func.lower(WormbaseGeneSummary.gene_id).startswith(query)
      )
    ).first()

  return result


def search_genes(query: str, species: str = None):
  """Query gene

  Query genes in the wormbase summary gene table.

  Args:
      query (str): Query string
      species (str, optional): Limit query to one species. If not provided, will query all species.

  Returns:
      results (list): List of dictionaries with gene results.
  """

  # Initialize search to match gene info with query
  search = or_(
    func.lower(WormbaseGeneSummary.locus).startswith(query),
    func.lower(WormbaseGeneSummary.sequence_name).startswith(query),
    func.lower(WormbaseGeneSummary.gene_id).startswith(query)
  )

  # If provided, add requirement that species matches
  if species is not None:
    search = and_( search, func.lower(WormbaseGeneSummary.species_name) == species )

  # Perform the query
  results = WormbaseGeneSummary.query.filter(search).limit(10).all()

  # Map to JSON and return
  results = [x.to_json() for x in results]
  return results


def search_homologs(query: str, species: str = None):
  """Query homolog

  Query the homologs database and return C. elegans homologs.

  Args:
      query (str): Query string
      species (str, optional): Limit query to one species. If not provided, will query all species.

  Returns:
      results (list): List of dictionaries describing the homolog.

  """

  # Extract query value from request or function argument
  query = request.args.get('query', query).lower()

  # Initialize search to match gene info with query
  search = (func.lower(Homolog.homolog_gene)).startswith(query)

  # If provided, add requirement that species matches
  if species is not None:
    search = and_( search, func.lower(Homolog.species_name) == species )

  # Perform the query
  results = Homolog.query.filter(search).limit(10).all()

  # Map to JSON and return
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
    return {
      'result': [{
        "chromosome": result.chrom,
        'start':      result.start,
        'end':        result.end,
      }],
    }
  else:
    return {'error': 'not found'}