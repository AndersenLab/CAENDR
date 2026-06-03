from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from caendr.services.cloud.postgresql import db
from caendr.models.sql.dict_serializable import DictSerializable

class WormbaseGene(DictSerializable, db.Model):
  id: Mapped[int] = mapped_column(Integer(), primary_key=True)
  species_name: Mapped[str] = mapped_column(String(20), index=True)
  chrom: Mapped[str] = mapped_column(String(20), index=True)
  chrom_num: Mapped[int] = mapped_column(Integer(), index=True)  # For sorting purposes
  start: Mapped[int] = mapped_column(Integer(), index=True)
  end: Mapped[int] = mapped_column(Integer(), index=True)
  feature: Mapped[str] = mapped_column(String(30), index=True)
  strand: Mapped[str] = mapped_column(String(1))
  frame: Mapped[int | None] = mapped_column(Integer())
  gene_id: Mapped[str] = mapped_column(ForeignKey('wormbase_gene_summary.gene_id'))
  gene_biotype: Mapped[str | None] = mapped_column(String(30))
  locus: Mapped[str | None] = mapped_column(String(30), index=True)
  transcript_id: Mapped[str | None] = mapped_column(String(30), index=True)
  transcript_biotype: Mapped[str | None] = mapped_column(String(), index=True)
  exon_id: Mapped[str | None] = mapped_column(String(30), index=True)
  exon_number: Mapped[int | None] = mapped_column(Integer())
  protein_id: Mapped[str | None] = mapped_column(String(50), index=True)
  arm_or_center: Mapped[str] = mapped_column(String(12), index=True)

  __tablename__ = 'wormbase_gene'
  __gene_summary__ = relationship(
    "WormbaseGeneSummary",
    backref='wormbase_gene',
    lazy='joined'
  )


  def __repr__(self):
    return f"{self.gene_id}:{self.feature} [{self.seqname}:{self.start}-{self.end}]"
