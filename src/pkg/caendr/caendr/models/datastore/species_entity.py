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


  @classmethod
  def query_ds_split_species(cls, filter=None):
    '''
      Query all entities of this type, splitting / partitioning by species field.
      Returns a dict mapping species names (IDs) to all Entities belonging to that species
    '''

    # Fill in default filter function, if needed
    if filter is None:
      filter = lambda e: True

    # Run the query for each species
    return {
      species: [
        e for e in cls.query_ds(filters=[('species', '=', species)]) if filter(e)
      ] for species in Species.all().keys()
    }
