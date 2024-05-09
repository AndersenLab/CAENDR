from caendr.services.cloud.postgresql     import db, rollback_on_error
from caendr.models.sql.dict_serializable  import DictSerializable

class PhenotypeDatabase(DictSerializable, db.Model):
  """
      Phenotype database table captures data related to various traits exhibited 
      by different strains. Each row represents a specific combination of strain, 
      trait, and the corresponding trait value
  """
  trait_name = db.Column(db.String())
  strain_name = db.Column(db.String(), primary_key=True)
  trait_value = db.Column(db.Float())
  metadata_id = db.Column(db.String(), db.ForeignKey('phenotype_metadata.id'), primary_key=True)

  __tablename__ = 'phenotype_db'


  def add_trait_data(self, trait_data):
    """
        Adds trait data to the Phenotype Database table
    """
    db.session.bulk_insert_mappings(PhenotypeDatabase, trait_data)
    db.session.commit()

  @classmethod
  @rollback_on_error
  def delete_by_metadata_id(cls, metadata_id):
    """
        Deletes entries from the Phenotype Database table for the given trait
    """

    del_statement = PhenotypeDatabase.__table__.delete().where(PhenotypeDatabase.metadata_id == metadata_id)
    db.session.execute(del_statement)
    db.session.commit()