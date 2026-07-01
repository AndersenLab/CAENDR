from sqlalchemy import and_, String, Integer, Float, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import pandas as pd

from caendr.services.cloud.postgresql import db
from caendr.models.sql.dict_serializable import DictSerializable
from caendr.utils.bio  import parse_chrom_interval, parse_chrom_position

from caendr.services.logger import logger



class Variant(db.Model):
  id: Mapped[int] = mapped_column(Integer(), primary_key=True)
  species_name: Mapped[str] = mapped_column(String(20), index=True)
  chrom: Mapped[str] = mapped_column(String(7), index=True)
  pos: Mapped[int] = mapped_column(Integer(), index=True)
  ref_seq: Mapped[str | None] = mapped_column(String())
  alt_seq: Mapped[str | None] = mapped_column(String())
  strains: Mapped[str | None] = mapped_column(String())
  divergent: Mapped[bool | None] = mapped_column(Boolean())
  release: Mapped[str | None] = mapped_column(String())

  __tablename__ = 'variants'
  name = "Variants"

  # List of columns to be checked by default
  _column_default_list = [
    "pos",
    "strains",
    "divergent"
  ]
  
  def __repr__(self):
    return f"Variant: {self.chrom} -- {self.pos}"

  @staticmethod
  def get_column_details():
    return [
      {'id': 'chrom', 'name': 'Chromosome', 'priority': 1},
      {'id': 'pos', 'name': 'Position', 'priority': 2},
      {'id': 'ref_seq', 'name': 'Reference Sequence', 'priority': 3},
      {'id': 'alt_seq', 'name': 'Alternative Sequence', 'priority': 4},
      {'id': 'strains', 'name': 'Strains', 'priority': 11},
      {'id': 'divergent', 'name': 'Hyper-Divergent Region', 'priority': 18},
      {'id': 'release', 'name': 'Release Date', 'priority': 19}
    ]
  
  @staticmethod
  def get_column_names():
    return [ col.get('id') for col in Variant.get_column_details()]

  @staticmethod
  def column_default_visibility(col):
    """
    Determine whether a column should be visible by default.
    Takes column object with 'id' field.
    Currently, this is based on a hard-coded list.  This can be changed to any desired filter.
    """
    return col['id'] in Variant._column_default_list


  @classmethod
  def run_interval_query(cls, interval, species):
    # If interval was passed as a string, parse into a dict
    # Otherwise, it should already be a dict with the right structure
    if isinstance(interval, str):
      interval = parse_chrom_interval(interval)
    # Construct the query object from the given interval
    query = db.select(cls).filter( and_(
      cls.species_name == species.name,
      cls.chrom == interval['chrom'],
      cls.pos > interval['start'],
      cls.pos < interval['stop'],
    ) )
    return cls.__run_query(query)

  @classmethod
  def run_position_query(cls, position, species):
    # If position was passed as a string, parse into a dict
    # Otherwise, it should already be a dict with the right structure
    if isinstance(position, str):
      position = parse_chrom_position(position)
    # Construct the query object from the given position
    query = db.select(cls).filter( and_(
      cls.species_name == species.name,
      cls.chrom == position['chrom'],
      cls.pos   == position['pos'],
    ) )
    return cls.__run_query(query)

  @classmethod
  def __run_query(cls, query):
    # Get the list of column names
    columns = cls.get_column_names()
    results = db.session.execute(query).scalars().all()
    results_dict = {getattr(row, 'id'): {col: getattr(row, col) for col in columns} for row in results}
    return results_dict
  
  @classmethod
  def query_all(cls, species):
    query = db.select(cls).filter(cls.species_name == species.name)
    results = db.session.execute(query).scalars().all()
    return {(getattr(row, 'chrom'), getattr(row, 'pos')): getattr(row, 'id') for row in results}

class GeneralAnnotatedVariant(DictSerializable):

  @classmethod
  def get_all_column_names(cls):
    columns = cls.get_column_details()
    columns += Variant.get_column_details()
    columns.sort(key=lambda x: x['priority'])
    return ['id'] + [col['id'] for col in columns]

  @classmethod
  def run_interval_query(cls, interval, species):
    # If interval was passed as a string, parse into a dict
    # Otherwise, it should already be a dict with the right structure
    if isinstance(interval, str):
      interval = parse_chrom_interval(interval)
    # Get variants covering interval
    variants = Variant.run_interval_query(interval=interval, species=species)
    # Find variant_id range
    variant_ids = list(variants.keys())
    min_id = min(variant_ids)
    max_id = max(variant_ids)
    # Construct the query object from the given interval
    query = db.select(cls).filter( and_(
      cls.variant_id >= min_id,
      cls.variant_id <= max_id,
    ) )
    return cls.__run_query(query, variants)


  @classmethod
  def run_position_query(cls, position, species):
    # If position was passed as a string, parse into a dict
    # Otherwise, it should already be a dict with the right structure
    if isinstance(position, str):
      position = parse_chrom_position(position)
    # Get variants covering interval
    variants = Variant.run_interval_query(interval=interval, species=species)
    # Find variant_id range
    variant_ids = list(variants.keys())
    min_id = min(variant_ids)
    max_id = max(variant_ids)
    # Construct the query object from the given interval
    query = db.select(cls).filter( and_(
      cls.variant_id >= min_id,
      cls.variant_id <= max_id,
    ) )
    return cls.__run_query(query, variants)

  @classmethod
  def __run_query(cls, query, variants):
    # Get the list of column names
    columns = cls.get_column_names()
    # Convert query into a DataFrame
    results = db.session.execute(query).scalars().all()
    results_dict = []
    for i, row in enumerate(results):
      variant_id = getattr(row, 'variant_id')
      new_row = {col: getattr(row, col) for col in columns}
      new_row.update(variants[variant_id])
      results_dict.append(new_row)
    # Add variants columns
    columns = cls.get_all_column_names()
    data_frame = pd.DataFrame(
      tuple(results_dict), columns=columns
    )
    try:
      result = data_frame[columns].dropna(how='all').fillna(value="").agg(list).to_dict()
    except ValueError:
      result = {}
    return result


class AnnovarAnnotatedVariant(GeneralAnnotatedVariant, db.Model):
  id: Mapped[int] = mapped_column(Integer(), primary_key=True)
  variant_id: Mapped[int] = mapped_column(ForeignKey('variants.id'), index=True)
  consequence: Mapped[str | None] = mapped_column(String())
  gene_id: Mapped[str | None] = mapped_column(ForeignKey('wormbase_gene_summary.gene_id'), index=True)
  transcript: Mapped[str | None] = mapped_column(String(), index=True)
  amino_acid_change: Mapped[str | None] = mapped_column(String())
  blosum: Mapped[int | None] = mapped_column(Integer())
  grantham: Mapped[int | None] = mapped_column(Integer())
  percent_protein: Mapped[float | None] = mapped_column(Float())
  gene: Mapped[str | None] = mapped_column(String(), index=True)
  variant_impact: Mapped[str | None] = mapped_column(String())

  __tablename__ = 'annovar_annotated_variants'
  __gene_summary__ = db.relationship("WormbaseGeneSummary", backref='annovar_annotated_variants', lazy='joined')
  __variant_id__ = db.relationship("Variant", backref='variants', lazy='joined')
  name = "Annovar"

  # List of columns to be checked by default
  _column_default_list = [
    "consequence",
    "amino_acid_change",
    "blosum",
    "grantham",
    "variant_impact",
  ]
  
  def __repr__(self):
    return f"Annovar Annotated Variant: {self.chrom} -- {self.pos}"

  @staticmethod
  def get_column_details():
    return [
      {'id': 'consequence', 'name': 'Consequence', 'priority': 6},
      {'id': 'gene_id', 'name': 'Gene ID', 'priority': 8},
      {'id': 'transcript', 'name': 'Transcript', 'priority': 9},
      {'id': 'amino_acid_change', 'name': 'Amino Acid Change', 'priority': 10},
      {'id': 'blosum', 'name': 'BLOSUM Score', 'priority': 12},
      {'id': 'grantham', 'name': 'Grantham Score', 'priority': 13},
      {'id': 'percent_protein', 'name': 'Percent Protein', 'priority': 15},
      {'id': 'gene', 'name': 'Gene', 'priority': 16},
      {'id': 'variant_impact', 'name': 'Variant Impact', 'priority': 17},
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
  variant_id: Mapped[int] = mapped_column(ForeignKey('variants.id'), index=True)
  consequence: Mapped[str | None] = mapped_column(String())
  target_consequence: Mapped[int | None] = mapped_column(Integer())
  gene_id: Mapped[str | None] = mapped_column(ForeignKey('wormbase_gene_summary.gene_id'), index=True)
  transcript: Mapped[str | None] = mapped_column(String(), index=True)
  amino_acid_change: Mapped[str | None] = mapped_column(String())
  dna_change: Mapped[str | None] = mapped_column(String())
  blosum: Mapped[int | None] = mapped_column(Integer())
  grantham: Mapped[int | None] = mapped_column(Integer())
  percent_protein: Mapped[float | None] = mapped_column(Float())
  gene: Mapped[str | None] = mapped_column(String(), index=True)

  __tablename__ = 'csq_annotated_variants'
  __gene_summary__ = db.relationship("WormbaseGeneSummary", backref='csq_annotated_variants', lazy='joined')
  __variant_id__ = db.relationship("Variant", backref='variants', lazy='joined')
  name = "CSQ"

  # List of columns to be checked by default
  _column_default_list = [
    "consequence",
    "amino_acid_change",
    "blosum",
    "grantham",
  ]
  
  def __repr__(self):
    return f"CSQ Annotated Variant: {self.chrom} -- {self.pos}"

  @staticmethod
  def get_column_details():
    return [
      {'id': 'consequence', 'name': 'Consequence', 'priority': 6},
      {'id': 'target_consequence', 'name': 'Target Consequence', 'priority': 7},
      {'id': 'gene_id', 'name': 'Gene ID', 'priority': 8},
      {'id': 'transcript', 'name': 'Transcript', 'priority': 9},
      {'id': 'amino_acid_change', 'name': 'Amino Acid Change', 'priority': 10},
      {'id': 'dna_change', 'name': 'DNA Change', 'priority': 11},
      {'id': 'blosum', 'name': 'BLOSUM Score', 'priority': 12},
      {'id': 'grantham', 'name': 'Grantham Score', 'priority': 13},
      {'id': 'percent_protein', 'name': 'Percent Protein', 'priority': 15},
      {'id': 'gene', 'name': 'Gene', 'priority': 16},
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
  variant_id: Mapped[int] = mapped_column(ForeignKey('variants.id'), index=True)
  consequence: Mapped[str | None] = mapped_column(String())
  gene_id: Mapped[str | None] = mapped_column(ForeignKey('wormbase_gene_summary.gene_id'), index=True)
  transcript: Mapped[str | None] = mapped_column(String(), index=True)
  amino_acid_change: Mapped[str | None] = mapped_column(String())
  grantham: Mapped[int | None] = mapped_column(Integer())
  percent_protein: Mapped[float | None] = mapped_column(Float())
  gene: Mapped[str | None] = mapped_column(String(), index=True)
  variant_impact: Mapped[str | None] = mapped_column(String())

  __tablename__ = 'snpeff_annotated_variants'
  __gene_summary__ = db.relationship("WormbaseGeneSummary", backref='snpeff_annotated_variants', lazy='joined')
  __variant_id__ = db.relationship("Variant", backref='variants', lazy='joined')
  name = "SnpEff"

  # List of columns to be checked by default
  _column_default_list = [
    "consequence",
    "amino_acid_change",
    "grantham",
    "variant_impact",
  ]
  
  def __repr__(self):
    return f"SnpEff Annotated Variant: {self.chrom} -- {self.pos}"

  @staticmethod
  def get_column_details():
    return [
      {'id': 'consequence', 'name': 'Consequence', 'priority': 6},
      {'id': 'gene_id', 'name': 'Gene ID', 'priority': 8},
      {'id': 'transcript', 'name': 'Transcript', 'priority': 9},
      {'id': 'amino_acid_change', 'name': 'Amino Acid Change', 'priority': 10},
      {'id': 'grantham', 'name': 'Grantham Score', 'priority': 13},
      {'id': 'percent_protein', 'name': 'Percent Protein', 'priority': 15},
      {'id': 'gene', 'name': 'Gene', 'priority': 16},
      {'id': 'variant_impact', 'name': 'Variant Impact', 'priority': 17},
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
  variant_id: Mapped[int] = mapped_column(ForeignKey('variants.id'), index=True)
  consequence: Mapped[str | None] = mapped_column(String())
  gene_id: Mapped[str | None] = mapped_column(ForeignKey('wormbase_gene_summary.gene_id'), index=True)
  transcript: Mapped[str | None] = mapped_column(String(), index=True)
  amino_acid_change: Mapped[str | None] = mapped_column(String())
  blosum: Mapped[int | None] = mapped_column(Integer())
  grantham: Mapped[int | None] = mapped_column(Integer())
  percent_protein: Mapped[float | None] = mapped_column(Float())
  gene: Mapped[str | None] = mapped_column(String(), index=True)
  variant_impact: Mapped[str | None] = mapped_column(String())

  __tablename__ = 'vep_annotated_variants'
  __gene_summary__ = db.relationship("WormbaseGeneSummary", backref='vep_annotated_variants', lazy='joined')
  __variant_id__ = db.relationship("Variant", backref='variants', lazy='joined')
  name = "VEP"

  # List of columns to be checked by default
  _column_default_list = [
    "consequence",
    "amino_acid_change",
    "blosum",
    "grantham",
    "variant_impact",
  ]
  
  def __repr__(self):
    return f"VEP Annotated Variant: {self.chrom} -- {self.pos}"

  @staticmethod
  def get_column_details():
    return [
      {'id': 'consequence', 'name': 'Consequence', 'priority': 6},
      {'id': 'gene_id', 'name': 'Gene ID', 'priority': 8},
      {'id': 'transcript', 'name': 'Transcript', 'priority': 9},
      {'id': 'amino_acid_change', 'name': 'Amino Acid Change', 'priority': 10},
      {'id': 'blosum', 'name': 'BLOSUM Score', 'priority': 12},
      {'id': 'grantham', 'name': 'Grantham Score', 'priority': 13},
      {'id': 'percent_protein', 'name': 'Percent Protein', 'priority': 15},
      {'id': 'gene', 'name': 'Gene', 'priority': 16},
      {'id': 'variant_impact', 'name': 'Variant Impact', 'priority': 17},
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
