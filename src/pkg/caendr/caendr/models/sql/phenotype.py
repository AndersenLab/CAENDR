from caendr.services.cloud.postgresql import db
from caendr.models.sql.dict_serializable import DictSerializable

class PhenotypeDatabase(DictSerializable, db.Model):
  """
      Phenotype database table captures data related to various traits exhibited 
      by different strains. Each row represents a specific combination of strain, 
      trait, and the corresponding trait value
  """
  trait_name = db.Column(db.String(), db.ForeignKey('phenotype_metadata.trait_name'), primary_key=True, nullable=False)
  strain_name = db.Column(db.String(), primary_key=True)
  trait_value = db.Column(db.Float())

  __tablename__ = 'phenotype_db'