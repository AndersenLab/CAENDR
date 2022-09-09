import pandas as pd

from caendr.services.cloud.postgresql import db
from caendr.models.sql.dict_serializable import DictSerializable

class StrainAnnotatedVariant(DictSerializable, db.Model):
  """
      The Strain Annotated Variant table combines several features linked to variants:
      Genetic location, base pairs affected, consequences of reading, gene information, 
      strains affected, and severity of impact
  """
  id = db.Column(db.Integer, primary_key=True)
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
  snpeff_impact = db.Column(db.String(), nullable=True)
  divergent = db.Column(db.Boolean(), nullable=True)
  release = db.Column(db.String(), nullable=True)

  __tablename__ = 'strain_annotated_variants'
  __gene_summary__ = db.relationship("WormbaseGeneSummary", backref='strain_annotated_variants', lazy='joined')
  
  
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
      {'id': 'snpeff_impact', 'name': 'SnpEff Impact'},
      {'id': 'divergent', 'name': 'Divergent'},
      {'id': 'release', 'name': 'Release Date'}
    ]


  @staticmethod
  def column_default_visibility(col):
    """
    Determine whether a column should be visible by default.

    Takes column object with 'id' field.

    Currently, this is based on a hard-coded list.  This can be changed to any desired filter.
    """

    default_list = [
      "pos",
      "consequence",
      "amino_acid_change",
      "strains",
      "blosum",
      "grantham",
      "variant_impact",
      "divergent"
    ]

    return col['id'] in default_list


  @classmethod
  def generate_interval_sql(cls, interval):
    interval = interval.replace(',','')
    chrom = interval.split(':')[0]
    range = interval.split(':')[1]
    start = int(range.split('-')[0])
    stop = int(range.split('-')[1])

    query = f"SELECT * FROM {cls.__tablename__} WHERE chrom='{chrom}' AND pos > {start} AND pos < {stop};"
    return query


  @classmethod
  def run_interval_query(cls, query):
    query = cls.generate_interval_sql(query)
    data_frame = pd.read_sql_query(query, db.engine)
    col_list = [ col.get('id') for col in cls.get_column_details()]
    cols = [ 'id', *col_list ]
    try:  
      test = data_frame[cols].dropna(how='all')
      print(test)
      result = data_frame[cols].dropna(how='all').fillna(value="").agg(list).to_dict()
    except ValueError:
      result = {}
    return result

  
  @classmethod
  def generate_position_sql(cls, pos):
    pos = pos.replace(',','')  
    chrom = pos.split(':')[0]
    pos = int(pos.split(':')[1])

    query = f"SELECT * FROM {cls.__tablename__} WHERE chrom='{chrom}' AND pos = {pos};"
    return query


  @classmethod
  def run_position_query(cls, query):
    query = cls.generate_position_sql(query)
    data_frame = pd.read_sql_query(query, db.engine)
    col_list = [ col.get('id') for col in cls.get_column_details()]
    cols = [ 'id', *col_list ]
    try:  
      result = data_frame[cols].dropna(how='all').fillna(value="").agg(list).to_dict()
    except ValueError:
      result = {}
    return result