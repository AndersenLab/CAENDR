from caendr.services.cloud.postgresql import db
from caendr.models.sql.dict_serializable import DictSerializable

class PhenotypeDatabase(DictSerializable, db.Model):
  """
      Table description
  """
  trait_name = db.Column(db.String(), primary_key=True)
  strain_name = db.Column(db.String(), primary_key=True)
  trait_value = db.Column(db.Float())

  __tablename__ = 'phenotype_db'