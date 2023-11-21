from functools import wraps

from flask import abort, redirect, request, url_for

from caendr.models.datastore import DatasetRelease, Species
from caendr.models.error     import NotFoundError



def parse_species_and_release(f):
  '''
    Parse `species_name` and `release_version` string arguments from the URL
    into a `Species` object and `DatasetRelease` object, respectively.

    If `release_version` is omitted, defaults to latest release for the given species.

    Aborts with `404` if either was not valid.
  '''

  @wraps(f)
  def decorator(*args, species_name, release_version=None, **kwargs):

    # Parse the species & release from the URL
    try:
      species = Species.from_name(species_name, from_url=True)
      release = DatasetRelease.from_name(release_version, species_name=species.name)

    # The `from_name` method always raises a NotFoundError if the name is not valid
    except NotFoundError:
      return abort(404)
    
    # If species name provided with underscore instead of dash, redirect to dashed version of URL
    if species.get_slug() != species_name:
      return redirect( url_for(request.endpoint, *args, species_name=species.get_slug(), release_version=release_version, **kwargs) )

    # Pass the objects to the function
    return f(*args, species=species, release=release, **kwargs)

  return decorator
