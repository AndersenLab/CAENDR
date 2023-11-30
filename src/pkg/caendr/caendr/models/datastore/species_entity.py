from caendr.models.datastore import Entity, Species



class SpeciesEntity(Entity):
  '''
    An `Entity` with a `'species'` field.

    Returns the `species` field as a `Species` entity.
  '''


  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'species',
    }


  @property
  def species(self):
    return Species.get( self._get_raw_prop('species') )
  
  @species.setter
  def species(self, v):
    if not isinstance(v, Species):
      v = Species.from_name(v)
    self._set_raw_prop( 'species', v.name )


  def serialize(self, include_meta=True):
    props = super().serialize(include_meta)

    # Replace the species field with its name
    if props.get('species') is not None and isinstance(props['species'], Species):
      props['species'] = props['species'].name

    return props
