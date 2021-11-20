from caendr.services.cloud.postgresql import db
from caendr.models.sql.dict_serializable import DictSerializable

class WormbaseGene(DictSerializable, db.Model):
  id = db.Column(db.Integer, primary_key=True)
  chrom = db.Column(db.String(20), index=True)
  chrom_num = db.Column(db.Integer(), index=True)  # For sorting purposes
  start = db.Column(db.Integer(), index=True)
  end = db.Column(db.Integer(), index=True)
  feature = db.Column(db.String(30), index=True)
  strand = db.Column(db.String(1))
  frame = db.Column(db.Integer(), nullable=True)
  gene_id = db.Column(db.ForeignKey('wormbase_gene_summary.gene_id'), nullable=False)
  gene_biotype = db.Column(db.String(30), nullable=True)
  locus = db.Column(db.String(30), index=True)
  transcript_id = db.Column(db.String(30), nullable=True, index=True)
  transcript_biotype = db.Column(db.String(), index=True)
  exon_id = db.Column(db.String(30), nullable=True, index=True)
  exon_number = db.Column(db.Integer(), nullable=True)
  protein_id = db.Column(db.String(30), nullable=True, index=True)
  arm_or_center = db.Column(db.String(12), index=True)
  
  __tablename__ = 'wormbase_gene'
  __gene_summary__ = db.relationship("WormbaseGeneSummary", backref='wormbase_gene', lazy='joined')


  def __repr__(self):
    return f"{self.gene_id}:{self.feature} [{self.seqname}:{self.start}-{self.end}]"
