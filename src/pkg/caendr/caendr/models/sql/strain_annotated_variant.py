import pandas as pd
from sqlalchemy import and_

from caendr.services.cloud.postgresql import db
from caendr.models.sql.dict_serializable import DictSerializable
from caendr.utils.bio  import parse_chrom_interval, parse_chrom_position
from caendr.utils.data import convert_query_to_data_table

class StrainAnnotatedVariant(DictSerializable, db.Model):
  """
      The Strain Annotated Variant table combines several features linked to variants:
      Genetic location, base pairs affected, consequences of reading, gene information, 
      strains affected, and severity of impact
  """
  id = db.Column(db.Integer, primary_key=True)
  species_name = db.Column(db.String(20), index=True)
  chrom = db.Column(db.String(7), index=True)
  pos = db.Column(db.Integer(), index=True)
  ref_seq = db.Column(db.String(), nullable=True)
  alt_seq = db.Column(db.String(), nullable=True)
  consequence = db.Column(db.String(), nullable=True)
  target_consequence = db.Column(db.Integer(), nullable=True)
  gene_id = db.Column(db.ForeignKey('wormbase_gene_summary.gene_id'), index=True, nullable=True)
  transcript = db.Column(db.String(), index=True, nullable=True)
  biotype = db.Column(db.String(), nullable=True)
  strand = db.Column(db.String(1), nullable=True)
  amino_acid_change = db.Column(db.String(), nullable=True)
  dna_change = db.Column(db.String(), nullable=True)
  strains = db.Column(db.String(), nullable=True)
  blosum = db.Column(db.Integer(), nullable=True)
  grantham = db.Column(db.Integer(), nullable=True)
  percent_protein = db.Column(db.Float(), nullable=True)
  gene = db.Column(db.String(), index=True, nullable=True)
  variant_impact = db.Column(db.String(), nullable=True)
  divergent = db.Column(db.Boolean(), nullable=True)
  release = db.Column(db.String(), nullable=True)

  __tablename__ = 'strain_annotated_variants'
  __gene_summary__ = db.relationship("WormbaseGeneSummary", backref='strain_annotated_variants', lazy='joined')


  # List of columns to be checked by default
  _column_default_list = [
    "pos",
    "consequence",
    "amino_acid_change",
    "strains",
    "blosum",
    "grantham",
    "variant_impact",
    "divergent"
  ]
  
  
  def __repr__(self):
    return f"Strain Annotated Variant: {self.chrom} -- {self.pos}"


  @staticmethod
  def get_column_details():
    return [
      {'id': 'chrom', 'name': 'Chromosome'},
      {'id': 'pos', 'name': 'Position'},
      {'id': 'ref_seq', 'name': 'Reference Sequence'},
      {'id': 'alt_seq', 'name': 'Alternative Sequence'},
      {'id': 'consequence', 'name': 'Consequence'},
      {'id': 'target_consequence', 'name': 'Target Consequence'},
      {'id': 'gene_id', 'name': 'Gene ID'},
      {'id': 'transcript', 'name': 'Transcript'},
      {'id': 'biotype', 'name': 'Biotype'},
      {'id': 'strand', 'name': 'Strand'},
      {'id': 'amino_acid_change', 'name': 'Amino Acid Change'},
      {'id': 'dna_change', 'name': 'DNA Change'},
      {'id': 'strains', 'name': 'Strains'},
      {'id': 'blosum', 'name': 'BLOSUM Score'},
      {'id': 'grantham', 'name': 'Grantham Score'},
      {'id': 'percent_protein', 'name': 'Percent Protein'},
      {'id': 'gene', 'name': 'Gene'},
      {'id': 'variant_impact', 'name': 'Variant Impact'},
      {'id': 'divergent', 'name': 'Divergent'},
      {'id': 'release', 'name': 'Release Date'}
    ]

  @staticmethod
  def get_column_names():
    return [ 'id', *[ col.get('id') for col in StrainAnnotatedVariant.get_column_details()] ]


  @staticmethod
  def column_default_visibility(col):
    """
    Determine whether a column should be visible by default.

    Takes column object with 'id' field.

    Currently, this is based on a hard-coded list.  This can be changed to any desired filter.
    """

    return col['id'] in StrainAnnotatedVariant._column_default_list



  @classmethod
  def run_interval_query(cls, interval, species=None):

    # If interval was passed as a string, parse into a dict
    # Otherwise, it should already be a dict with the right structure
    if isinstance(interval, str):
      interval = parse_chrom_interval(interval, silent=False)

    # Construct the query object from the given interval
    query = StrainAnnotatedVariant.query.filter( and_(
      StrainAnnotatedVariant.chrom == interval['chrom'],
      StrainAnnotatedVariant.pos > interval['start'],
      StrainAnnotatedVariant.pos < interval['stop'],
    ) )

    return cls.__run_query(query, species=species)


  @classmethod
  def run_position_query(cls, position, species=None):

    # If position was passed as a string, parse into a dict
    # Otherwise, it should already be a dict with the right structure
    if isinstance(position, str):
      position = parse_chrom_position(position, silent=False)

    # Construct the query object from the given position
    query = StrainAnnotatedVariant.query.filter( and_(
      StrainAnnotatedVariant.chrom == position['chrom'],
      StrainAnnotatedVariant.pos   == position['pos'],
    ) )

    return cls.__run_query(query, species=species)


  @classmethod
  def __run_query(cls, query, species=None):

    # Get the list of column names
    columns = StrainAnnotatedVariant.get_column_names()

    # If a species was provided, use it to refine the query
    if species:
      query = query.filter( StrainAnnotatedVariant.species_name == species.name )

    # Convert query into a DataFrame
    data_frame = convert_query_to_data_table(query, columns=columns)

    try:
      result = data_frame[columns].dropna(how='all').fillna(value="").agg(list).to_dict()
    except ValueError:
      result = {}
    return result



_full_column_list = list(map( lambda x: x['id'], StrainAnnotatedVariant.get_column_details() ))

for col_id in StrainAnnotatedVariant._column_default_list:
  assert col_id in _full_column_list, f'Could not set column ID "{col_id}" to checked by default - ID was not found. Is this a typo?'
