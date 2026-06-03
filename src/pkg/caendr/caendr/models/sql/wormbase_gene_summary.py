from sqlalchemy import or_, String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property

from caendr.services.cloud.postgresql import db
from caendr.models.sql.dict_serializable import DictSerializable

class WormbaseGeneSummary(DictSerializable, db.Model):
  """
      This is a condensed version of the WormbaseGene model;
      It is constructed out of convenience and only defines the genes
      (not exons/introns/etc.)
  """
  id: Mapped[int] = mapped_column(Integer(), primary_key=True)
  species_name: Mapped[str] = mapped_column(String(20), index=True)
  chrom: Mapped[str] = mapped_column(String(7), index=True)
  chrom_num: Mapped[int] = mapped_column(Integer(), index=True)
  start: Mapped[int] = mapped_column(Integer(), index=True)
  end: Mapped[int] = mapped_column(Integer(), index=True)
  locus: Mapped[str | None] = mapped_column(String(30), index=True)
  gene_id: Mapped[str] = mapped_column(String(25), unique=True, index=True)
  gene_id_type: Mapped[str] = mapped_column(String(15), index=False)
  sequence_name: Mapped[str] = mapped_column(String(30), index=True)
  biotype: Mapped[str | None] = mapped_column(String(30))
  gene_symbol: Mapped[str | None] = mapped_column(String(30))
  arm_or_center: Mapped[str] = mapped_column(String(12), index=True)

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
    result = db.session.execute(
      db.select(cls).filter(or_(cls.locus == query, cls.sequence_name == query))
    ).scalar_one_or_none()
    if result:
      return result.gene_id
