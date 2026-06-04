from sqlalchemy import and_, String, Integer, Float, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from caendr.services.cloud.postgresql import db
from caendr.models.sql.dict_serializable import DictSerializable
from caendr.utils.bio  import parse_chrom_interval, parse_chrom_position
from caendr.utils.data import convert_query_to_data_table

class GeneralAnnotatedVariant(DictSerializable):

  @classmethod
  def run_interval_query(cls, interval, species=None):
    # If interval was passed as a string, parse into a dict
    # Otherwise, it should already be a dict with the right structure
    if isinstance(interval, str):
      interval = parse_chrom_interval(interval)
    # Construct the query object from the given interval
    query = db.select(cls).filter( and_(
      cls.chrom == interval['chrom'],
      cls.pos > interval['start'],
      cls.pos < interval['stop'],
    ) )
    return cls.__run_query(query, species=species)


  @classmethod
  def run_position_query(cls, position, species=None):
    # If position was passed as a string, parse into a dict
    # Otherwise, it should already be a dict with the right structure
    if isinstance(position, str):
      position = parse_chrom_position(position)
    # Construct the query object from the given position
    query = db.select(cls).filter( and_(
      cls.chrom == position['chrom'],
      cls.pos   == position['pos'],
    ) )
    return cls.__run_query(query, species=species)

  @classmethod
  def __run_query(cls, query, species=None):
    # Get the list of column names
    columns = cls.get_column_names()
    # If a species was provided, use it to refine the query
    if species:
      query = query.filter( cls.species_name == species.name )
    # Convert query into a DataFrame
    data_frame = convert_query_to_data_table(query, columns=columns, db=db)
    try:
      result = data_frame[columns].dropna(how='all').fillna(value="").agg(list).to_dict()
    except ValueError:
      result = {}
    return result


class AnnovarAnnotatedVariant(GeneralAnnotatedVariant, db.Model):
  id: Mapped[int] = mapped_column(Integer(), primary_key=True)
  species_name: Mapped[str] = mapped_column(String(20), index=True, primary_key=True)
  chrom: Mapped[str] = mapped_column(String(7), index=True)
  pos: Mapped[int] = mapped_column(Integer(), index=True)
  ref_seq: Mapped[str | None] = mapped_column(String())
  alt_seq: Mapped[str | None] = mapped_column(String())
  consequence: Mapped[str | None] = mapped_column(String())
  target_consequence: Mapped[int | None] = mapped_column(Integer())
  gene_id: Mapped[str | None] = mapped_column(ForeignKey('wormbase_gene_summary.gene_id'), index=True)
  transcript: Mapped[str | None] = mapped_column(String(), index=True)
  amino_acid_change: Mapped[str | None] = mapped_column(String())
  strains: Mapped[str | None] = mapped_column(String())
  blosum: Mapped[int | None] = mapped_column(Integer())
  grantham: Mapped[int | None] = mapped_column(Integer())
  percent_protein: Mapped[float | None] = mapped_column(Float())
  gene: Mapped[str | None] = mapped_column(String(), index=True)
  variant_impact: Mapped[str | None] = mapped_column(String())
  divergent: Mapped[bool | None] = mapped_column(Boolean())
  release: Mapped[str | None] = mapped_column(String())

  __tablename__ = 'annovar_annotated_variants'
  __gene_summary__ = db.relationship("WormbaseGeneSummary", backref='annovar_annotated_variants', lazy='joined')
  name = "Annovar"

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
    return f"Annovar Annotated Variant: {self.chrom} -- {self.pos}"

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
      {'id': 'amino_acid_change', 'name': 'Amino Acid Change'},
      {'id': 'strains', 'name': 'Strains'},
      {'id': 'blosum', 'name': 'BLOSUM Score'},
      {'id': 'grantham', 'name': 'Grantham Score'},
      {'id': 'percent_protein', 'name': 'Percent Protein'},
      {'id': 'gene', 'name': 'Gene'},
      {'id': 'variant_impact', 'name': 'Variant Impact'},
      {'id': 'divergent', 'name': 'Hyper-Divergent Region'},
      {'id': 'release', 'name': 'Release Date'}
    ]
  
  @staticmethod
  def get_column_names():
    return [ 'id', *[ col.get('id') for col in AnnovarAnnotatedVariant.get_column_details()] ]

  @staticmethod
  def column_default_visibility(col):
    """
    Determine whether a column should be visible by default.
    Takes column object with 'id' field.
    Currently, this is based on a hard-coded list.  This can be changed to any desired filter.
    """
    return col['id'] in AnnovarAnnotatedVariant._column_default_list


class CsqAnnotatedVariant(GeneralAnnotatedVariant, db.Model):
  id: Mapped[int] = mapped_column(Integer(), primary_key=True)
  species_name: Mapped[str] = mapped_column(String(20), index=True, primary_key=True)
  chrom: Mapped[str] = mapped_column(String(7), index=True)
  pos: Mapped[int] = mapped_column(Integer(), index=True)
  ref_seq: Mapped[str | None] = mapped_column(String())
  alt_seq: Mapped[str | None] = mapped_column(String())
  consequence: Mapped[str | None] = mapped_column(String())
  target_consequence: Mapped[int | None] = mapped_column(Integer())
  gene_id: Mapped[str | None] = mapped_column(ForeignKey('wormbase_gene_summary.gene_id'), index=True)
  transcript: Mapped[str | None] = mapped_column(String(), index=True)
  amino_acid_change: Mapped[str | None] = mapped_column(String())
  dna_change: Mapped[str | None] = mapped_column(String())
  strains: Mapped[str | None] = mapped_column(String())
  blosum: Mapped[int | None] = mapped_column(Integer())
  grantham: Mapped[int | None] = mapped_column(Integer())
  percent_protein: Mapped[float | None] = mapped_column(Float())
  gene: Mapped[str | None] = mapped_column(String(), index=True)
  divergent: Mapped[bool | None] = mapped_column(Boolean())
  release: Mapped[str | None] = mapped_column(String())

  __tablename__ = 'csq_annotated_variants'
  __gene_summary__ = db.relationship("WormbaseGeneSummary", backref='csq_annotated_variants', lazy='joined')
  name = "CSQ"

  # List of columns to be checked by default
  _column_default_list = [
    "pos",
    "consequence",
    "amino_acid_change",
    "strains",
    "blosum",
    "grantham",
    "divergent"
  ]
  
  def __repr__(self):
    return f"CSQ Annotated Variant: {self.chrom} -- {self.pos}"

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
      {'id': 'amino_acid_change', 'name': 'Amino Acid Change'},
      {'id': 'dna_change', 'name': 'DNA Change'},
      {'id': 'strains', 'name': 'Strains'},
      {'id': 'blosum', 'name': 'BLOSUM Score'},
      {'id': 'grantham', 'name': 'Grantham Score'},
      {'id': 'percent_protein', 'name': 'Percent Protein'},
      {'id': 'gene', 'name': 'Gene'},
      {'id': 'divergent', 'name': 'Hyper-Divergent Region'},
      {'id': 'release', 'name': 'Release Date'}
    ]

  @staticmethod
  def get_column_names():
    return [ 'id', *[ col.get('id') for col in CsqAnnotatedVariant.get_column_details()] ]

  @staticmethod
  def column_default_visibility(col):
    """
    Determine whether a column should be visible by default.
    Takes column object with 'id' field.
    Currently, this is based on a hard-coded list.  This can be changed to any desired filter.
    """
    return col['id'] in CsqAnnotatedVariant._column_default_list


class SnpEffAnnotatedVariant(GeneralAnnotatedVariant, db.Model):
  id: Mapped[int] = mapped_column(Integer(), primary_key=True)
  species_name: Mapped[str] = mapped_column(String(20), index=True, primary_key=True)
  chrom: Mapped[str] = mapped_column(String(7), index=True)
  pos: Mapped[int] = mapped_column(Integer(), index=True)
  ref_seq: Mapped[str | None] = mapped_column(String())
  alt_seq: Mapped[str | None] = mapped_column(String())
  consequence: Mapped[str | None] = mapped_column(String())
  target_consequence: Mapped[int | None] = mapped_column(Integer())
  gene_id: Mapped[str | None] = mapped_column(ForeignKey('wormbase_gene_summary.gene_id'), index=True)
  transcript: Mapped[str | None] = mapped_column(String(), index=True)
  amino_acid_change: Mapped[str | None] = mapped_column(String())
  strains: Mapped[str | None] = mapped_column(String())
  grantham: Mapped[int | None] = mapped_column(Integer())
  percent_protein: Mapped[float | None] = mapped_column(Float())
  gene: Mapped[str | None] = mapped_column(String(), index=True)
  locus: Mapped[str | None] = mapped_column(String(), index=True)
  variant_impact: Mapped[str | None] = mapped_column(String())
  release: Mapped[str | None] = mapped_column(String())

  __tablename__ = 'snpeff_annotated_variants'
  __gene_summary__ = db.relationship("WormbaseGeneSummary", backref='snpeff_annotated_variants', lazy='joined')
  name = "SnpEff"

  # List of columns to be checked by default
  _column_default_list = [
    "pos",
    "consequence",
    "amino_acid_change",
    "strains",
    "grantham",
    "variant_impact",
    "divergent"
  ]
  
  def __repr__(self):
    return f"SnpEff Annotated Variant: {self.chrom} -- {self.pos}"

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
      {'id': 'amino_acid_change', 'name': 'Amino Acid Change'},
      {'id': 'strains', 'name': 'Strains'},
      {'id': 'grantham', 'name': 'Grantham Score'},
      {'id': 'percent_protein', 'name': 'Percent Protein'},
      {'id': 'gene', 'name': 'Gene'},
      {'id': 'locus', 'name': 'Locus'},
      {'id': 'variant_impact', 'name': 'Variant Impact'},
      {'id': 'release', 'name': 'Release Date'}
    ]

  @staticmethod
  def get_column_names():
    return [ 'id', *[ col.get('id') for col in SnpEffAnnotatedVariant.get_column_details()] ]

  @staticmethod
  def column_default_visibility(col):
    """
    Determine whether a column should be visible by default.
    Takes column object with 'id' field.
    Currently, this is based on a hard-coded list.  This can be changed to any desired filter.
    """
    return col['id'] in SnpEffAnnotatedVariant._column_default_list


class VepAnnotatedVariant(GeneralAnnotatedVariant, db.Model):
  id: Mapped[int] = mapped_column(Integer(), primary_key=True)
  species_name: Mapped[str] = mapped_column(String(20), index=True, primary_key=True)
  chrom: Mapped[str] = mapped_column(String(7), index=True)
  pos: Mapped[int] = mapped_column(Integer(), index=True)
  ref_seq: Mapped[str | None] = mapped_column(String())
  alt_seq: Mapped[str | None] = mapped_column(String())
  consequence: Mapped[str | None] = mapped_column(String())
  target_consequence: Mapped[int | None] = mapped_column(Integer())
  gene_id: Mapped[str | None] = mapped_column(ForeignKey('wormbase_gene_summary.gene_id'), index=True)
  transcript: Mapped[str | None] = mapped_column(String(), index=True)
  amino_acid_change: Mapped[str | None] = mapped_column(String())
  strains: Mapped[str | None] = mapped_column(String())
  blosum: Mapped[int | None] = mapped_column(Integer())
  grantham: Mapped[int | None] = mapped_column(Integer())
  percent_protein: Mapped[float | None] = mapped_column(Float())
  gene: Mapped[str | None] = mapped_column(String(), index=True)
  variant_impact: Mapped[str | None] = mapped_column(String())
  divergent: Mapped[bool | None] = mapped_column(Boolean())
  release: Mapped[str | None] = mapped_column(String())

  __tablename__ = 'vep_annotated_variants'
  __gene_summary__ = db.relationship("WormbaseGeneSummary", backref='vep_annotated_variants', lazy='joined')
  name = "VEP"

  # List of columns to be checked by default
  _column_default_list = [
    "pos",
    "consequence",
    "amino_acid_change",
    "strains",
    "blosum",
    "grantham",
    "variant_impact",
  ]
  
  def __repr__(self):
    return f"VEP Annotated Variant: {self.chrom} -- {self.pos}"

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
      {'id': 'amino_acid_change', 'name': 'Amino Acid Change'},
      {'id': 'strains', 'name': 'Strains'},
      {'id': 'blosum', 'name': 'BLOSUM Score'},
      {'id': 'grantham', 'name': 'Grantham Score'},
      {'id': 'percent_protein', 'name': 'Percent Protein'},
      {'id': 'gene', 'name': 'Gene'},
      {'id': 'variant_impact', 'name': 'Variant Impact'},
      {'id': 'divergent', 'name': 'Hyper-Divergent Region'},
      {'id': 'release', 'name': 'Release Date'}
    ]
  
  @staticmethod
  def get_column_names():
    return [ 'id', *[ col.get('id') for col in VepAnnotatedVariant.get_column_details()] ]

  @staticmethod
  def column_default_visibility(col):
    """
    Determine whether a column should be visible by default.
    Takes column object with 'id' field.
    Currently, this is based on a hard-coded list.  This can be changed to any desired filter.
    """
    return col['id'] in VepAnnotatedVariant._column_default_list
