from caendr.services.cloud.postgresql import db
from caendr.models.sql.dict_serializable import DictSerializable
from sqlalchemy import func, or_
from sqlalchemy.ext.hybrid import hybrid_property

class WormbaseGeneSummary(DictSerializable, db.Model):
  """
      This is a condensed version of the WormbaseGene model;
      It is constructed out of convenience and only defines the genes
      (not exons/introns/etc.)
  """
  id = db.Column(db.Integer, primary_key=True)
  chrom = db.Column(db.String(7), index=True)
  chrom_num = db.Column(db.Integer(), index=True)
  start = db.Column(db.Integer(), index=True)
  end = db.Column(db.Integer(), index=True)
  locus = db.Column(db.String(30), index=True)
  gene_id = db.Column(db.String(25), unique=True, index=True)
  gene_id_type = db.Column(db.String(15), index=False)
  sequence_name = db.Column(db.String(30), index=True)
  biotype = db.Column(db.String(30), nullable=True)
  gene_symbol = db.column_property(func.coalesce(locus, sequence_name, gene_id))
  # interval = db.column_property(func.format("%s:%s-%s", chrom, start, end))
  arm_or_center = db.Column(db.String(12), index=True)

  __tablename__ = "wormbase_gene_summary"
  __gene_id_constraint__ = db.UniqueConstraint(gene_id)

  @hybrid_property
  def interval(self):
    return f"{self.chrom}:{self.start}-{self.end}"    

  # TODO: move this somewhere else
  @classmethod
  def resolve_gene_id(cls, query):
    """
        query - a locus name or transcript ID
        output - a wormbase gene ID

        Example:
        WormbaseGene.resolve_gene_id('pot-2') --> WBGene00010195
    """
    result = cls.query.filter(or_(cls.locus == query, cls.sequence_name == query)).first()
    if result:
      return result.gene_id
