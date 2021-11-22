from caendr.services.cloud.postgresql import db
from caendr.models.sql.dict_serializable import DictSerializable

class Homolog(DictSerializable, db.Model):
  id = db.Column(db.Integer, primary_key=True)
  gene_id = db.Column(db.ForeignKey('wormbase_gene_summary.gene_id'), nullable=True, index=True)
  gene_name = db.Column(db.String(60), index=True)
  homolog_species = db.Column(db.String(60), index=True)
  homolog_taxon_id = db.Column(db.Integer, index=True, nullable=True)  # If available
  homolog_gene = db.Column(db.String(60), index=True)
  homolog_source = db.Column(db.String(60))
  is_ortholog = db.Column(db.Boolean(), index=True, nullable=True)

  __tablename__ = "homologs"
  __gene_summary__ = db.relationship("WormbaseGeneSummary", backref='homologs', lazy='joined')
  
  
  def __repr__(self):
    return f"homolog: {self.gene_name} -- {self.homolog_gene}"
  
  
  
'''
  def unnest(self):
    """
        Used with the gene API - returns
        an unnested homolog datastructure combined with the wormbase gene summary model.
    """
    self.__dict__.update(self.__gene_summary__.__dict__)
    return self
'''

