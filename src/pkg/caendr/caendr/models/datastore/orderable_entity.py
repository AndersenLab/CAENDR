from caendr.models.datastore import Entity


class OrderableEntity(Entity):
  '''
    Subclass of Entity for objects that are ordered relative to one another.

    Should never be instantiated directly -- in fact, this is prevented in this class's __new__ function.
    Instead, specific entity types should be subclasses of this class.
  '''
  
  def __new__(cls, *args, **kwargs):
    if cls is OrderableEntity:
      raise TypeError(f"Class '{cls.__name__}' should never be instantiated directly -- subclasses should be used instead.")
    return super(OrderableEntity, cls).__new__(cls)


  @classmethod
  def get_props_set(cls):
    return {
      *super().get_props_set(),
      'order',
    }


  @classmethod
  def query_ds(cls, *args, **kwargs):
    results = super().query_ds(*args, **kwargs)
    if 'order' not in kwargs:
      results = [
        *sorted([x for x in results if x['order'] is not None], key = lambda x: x['order']),
        *[x for x in results if x['order'] is None],
      ]
    return results
