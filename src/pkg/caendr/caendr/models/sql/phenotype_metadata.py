from datetime import datetime, timezone

from caendr.services.cloud.postgresql import db, rollback_on_error
from caendr.models.sql.dict_serializable import DictSerializable

from caendr.models.status import PublishStatus

from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship


class PhenotypeMetadata(DictSerializable, db.Model):
  """
      Phenotype Metadata table serves as a repository for metadata associated with various traits. 
      It complements a system where trait-related information is stored in the PhenotypeDatabase table. 
      This table includes details such as species, description, source lab, and other additional 
      information.
  """
  id: Mapped[str] = mapped_column(String(), primary_key=True)
  trait_name_user: Mapped[str | None] = mapped_column(String())
  trait_name_caendr: Mapped[str] = mapped_column(String())
  trait_name_display_1: Mapped[str | None] = mapped_column(String())
  trait_name_display_2: Mapped[str | None] = mapped_column(String())
  trait_name_display_3: Mapped[str | None] = mapped_column(String())
  species_name: Mapped[str] = mapped_column(String())
  wbgene_id: Mapped[str | None] = mapped_column(String())
  description_short: Mapped[str | None] = mapped_column(String())
  description_long: Mapped[str | None] = mapped_column(String())
  units: Mapped[str | None] = mapped_column(String())
  publication: Mapped[str | None] = mapped_column(String())
  protocols: Mapped[str | None] = mapped_column(String())
  source_lab: Mapped[str| None] = mapped_column(String())
  institution: Mapped[str | None] = mapped_column(String())
  submitted_by: Mapped[str] = db.Column(String())
  tags: Mapped[str | None] = db.Column(String())
  capture_date: Mapped[datetime | None] = mapped_column(DateTime())
  created_on: Mapped[datetime | None] = mapped_column(DateTime())
  modified_on: Mapped[datetime | None] = db.Column(db.DateTime())
  dataset: Mapped[str | None] =  mapped_column(String())
  is_bulk_file: Mapped[bool | None] = mapped_column(Boolean())
  publish_status: Mapped[str | None] = mapped_column(String)

  phenotype_values = relationship(
                      "PhenotypeDatabase",
                      backref='phenotype_db.metadata_id', 
                      primaryjoin='PhenotypeMetadata.id==PhenotypeDatabase.metadata_id', 
                      lazy='select'
                    )

  __tablename__ = 'phenotype_metadata'



  def to_json_with_values(self):
    """
      Converts PhenotypeMetadata instance to JSON in the joined queries
    """
    json_trait = self.to_json()
    phenotype_values = [ v.to_json() for v in self.phenotype_values ]
    json_trait['phenotype_values'] = phenotype_values
    return json_trait


  def get_tags(self):
    '''
      Get the category tags as a set of strings.
      If no tag set defined, returns None.
    '''
    if self.tags:
      return { tg.strip().lower() for tg in self.tags.split(',') }


  def add(self, trait_obj):
    new_trait = PhenotypeMetadata(
      id                   = trait_obj.name,
      trait_name_user      = trait_obj['trait_name_user'],
      trait_name_display_1 = trait_obj['trait_name_display_1'],
      trait_name_display_2 = trait_obj['trait_name_display_2'],
      trait_name_display_3 = trait_obj['trait_name_display_3'],
      species_name         = trait_obj['species'].name,
      wbgene_id            = 'N/A',
      description_short    = trait_obj['description_short'],
      description_long     = trait_obj['description_long'],
      units                = trait_obj['units'],
      publication          = trait_obj['publication'],
      protocols            = trait_obj['protocols'],
      source_lab           = trait_obj['source_lab'],
      institution          = trait_obj['institution'],
      submitted_by         = trait_obj.get_user_full_name(),
      tags                 = ', '.join(trait_obj['tags']),
      created_on           = datetime.now(timezone.utc),
      modified_on          = datetime.now(timezone.utc),
      dataset              = trait_obj['dataset'].value,
      is_bulk_file         = trait_obj['is_bulk_file'],
      publish_status       = trait_obj['publish_status'].value,
    )
    db.session.add(new_trait)
    db.session.commit()


  def delete(self):
    db.session.delete(self)
    db.session.commit()


  @rollback_on_error
  def set_status(self, new_status: PublishStatus):
    '''
      Set the `publish_status` of this entry and commit the change.
    '''

    # Validate argument type
    if not isinstance(new_status, PublishStatus):
      raise ValueError(f'Cannot set publish_status to {new_status}')

    # Set to the name field and commit
    self.publish_status = new_status.name
    db.session.commit()


  def update(self, **kwargs):
    for k, v in kwargs.items():
      if isinstance(v, list):
        v = ', '.join(v)
      setattr(self, k, v)
    setattr(self, 'modified_on', datetime.now(timezone.utc))
    db.session.commit()
