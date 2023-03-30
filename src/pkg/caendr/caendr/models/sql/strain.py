from caendr.services.cloud.postgresql import db
from caendr.models.sql.dict_serializable import DictSerializable

class Strain(DictSerializable, db.Model):
  species_id_method = db.Column(db.String(50), nullable=True)
  species = db.Column(db.String(50), index=True)
  species_name = db.Column(db.String(20), index=True)
  isotype_ref_strain = db.Column(db.Boolean(), index=True)
  strain = db.Column(db.String(25), primary_key=True)
  isotype = db.Column(db.String(25), index=True, nullable=True)
  previous_names = db.Column(db.String(100), nullable=True)
  sequenced = db.Column(db.Boolean(), index=True, nullable=True)  # Is whole genome sequenced [WGS_seq]
  release = db.Column(db.Integer(), nullable=False, index=True)
  source_lab = db.Column(db.String(), nullable=True)
  latitude = db.Column(db.Float(), nullable=True)
  longitude = db.Column(db.Float(), nullable=True)
  landscape = db.Column(db.String(), nullable=True)
  locality_description = db.Column(db.String(), nullable=True)
  substrate = db.Column(db.String(), nullable=True)
  substrate_comments = db.Column(db.String(), nullable=True)
  substrate_temp = db.Column(db.Float())
  ambient_temp = db.Column(db.Float())
  ambient_humidity = db.Column(db.Float())
  associated_organism = db.Column(db.String(), nullable=True)
  inbreeding_status = db.Column(db.String(), nullable=True)
  sampled_by = db.Column(db.String(), nullable=True)
  isolated_by = db.Column(db.String(), nullable=True)
  sampling_date = db.Column(db.Date(), nullable=True)
  sampling_date_comment = db.Column(db.String(), nullable=True)
  notes = db.Column(db.String(), nullable=True)
  strain_set = db.Column(db.String(), nullable=True)
  issues = db.Column(db.Boolean(), nullable=True)
  issue_notes = db.Column(db.String(), nullable=True)
  elevation = db.Column(db.Float(), nullable=True)
  
  __tablename__ = "strain"


  def __repr__(self):
    return self.strain
