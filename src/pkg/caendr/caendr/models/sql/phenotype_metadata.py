from caendr.services.cloud.postgresql import db
from caendr.models.sql.dict_serializable import DictSerializable

class PhenotypeMetadata(DictSerializable, db.Model):
  """
      Phenotype Metadata table serves as a repository for metadata associated with various traits. 
      It complements a system where trait-related information is stored in the PhenotypeDatabase table. 
      This table includes details such as species, description, source lab, and other additional 
      information.
  """
  trait_name = db.Column(db.String(), unique=True, primary_key=True)
  species = db.Column(db.String(20))
  description_short = db.Column(db.String(), nullable=True)
  description_long = db.Column(db.Text(), nullable=True)
  units = db.Column(db.String(), nullable=True)
  doi = db.Column(db.String(), nullable=True)
  protocols = db.Column(db.String(), nullable=True)
  source_lab = db.Column(db.String())
  created_on = db.Column(db.Date())
  phenotype_values = db.relationship('PhenotypeDatabase', backref='phenotype_db', lazy='joined')

  __tablename__ = 'phenotype_metadata'

