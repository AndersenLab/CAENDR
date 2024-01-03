from caendr.services.cloud.postgresql import db
from caendr.models.sql.dict_serializable import DictSerializable

class PhenotypeMetadata(DictSerializable, db.Model):
  """
      Phenotype Metadata table serves as a repository for metadata associated with various traits. 
      It complements a system where trait-related information is stored in the PhenotypeDatabase table. 
      This table includes details such as species, description, source lab, and other additional 
      information.
  """

  trait_name_caendr = db.Column(db.String(), unique=True, primary_key=True)
  trait_name_user = db.Column(db.String(), nullable=True)
  species = db.Column(db.String())
  wbgene_id = db.Column(db.String(), nullable=True)
  description_short = db.Column(db.String(), nullable=True)
  description_long = db.Column(db.Text(), nullable=True)
  units = db.Column(db.String(), nullable=True)
  publication = db.Column(db.String(), nullable=True)
  protocols = db.Column(db.String(), nullable=True)
  source_lab = db.Column(db.String())
  institution = db.Column(db.String())
  submitted_by = db.Column(db.String())
  tags = db.Column(db.String(), nullable=True)
  capture_date = db.Column(db.Date(), nullable=True)
  created_on = db.Column(db.Date(), nullable=False)
  modified_on = db.Column(db.Date())
  dataset = db.Column(db.String(), nullable=True)
  is_bulk_file = db.Column(db.Boolean(), nullable=False)
  phenotype_values = db.relationship(
                      'PhenotypeDatabase', 
                      backref='phenotype_db.trait_name', 
                      primaryjoin='PhenotypeMetadata.trait_name_caendr==PhenotypeDatabase.trait_name', 
                      lazy='select')

  __tablename__ = 'phenotype_metadata'

