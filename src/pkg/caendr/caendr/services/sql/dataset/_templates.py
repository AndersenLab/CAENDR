from logzero import logger

from string import Template
from logzero import logger

from caendr.models.error import BadRequestError

from ._env import external_db_url_templates, internal_db_blob_templates



## URLs ##

def url_template_type(db_url_name: str):
    '''
      Determines whether a URL is 'generic' (same for all species) or 'specific' (different for different species).
        Args:
          db_url_name (str): [Name of the URL template to check.]
        Raises:
          BadRequestError: [Provided URL name is not recognized.]
        Returns:
          str: ['generic' or 'specific']
    '''
    if db_url_name in external_db_url_templates['generic']:
      return 'generic'
    elif db_url_name in external_db_url_templates['specific']:
      return 'specific'
    else:
      logger.warning(f'Unrecognized URL template name "{db_url_name}".')
      raise BadRequestError()


def get_url_template(db_url_name: str):
    '''
      Gets the URL template associated with a given template name.
        Args:
          db_url_name (str): [The name of the template to retrieve.]
        Returns:
          str: [The URL template associated with the given name.]
    '''
    return external_db_url_templates[url_template_type(db_url_name)][db_url_name]


def get_url(self, db_url_name: str, species_name: str = None):
    '''
      Fills in the specified URL template with version & species information.  Some templates do not require a species.
        Args:
          db_url_name (str): [The name of the template to retrieve.]
          species_name (str, optional): [The species to fill in the template with. Defaults to None. Optional, but must be provided for certain templates.]
        Raises:
          BadRequestError: [Class-level WormBase version not set; URL template requires species, but none provided; Unknown species name.]
        Returns:
          str: [The desired URL filled in with information for the given species.]
    '''
    # Make sure a species name was provided if the URL requires one
    if (url_template_type(db_url_name) == 'specific') and species_name is None:
      logger.warning(f'URL template "{db_url_name}" requires a species, but none was provided.')
      raise BadRequestError()

    # Make sure the species name is valid
    if species_name is not None and species_name not in self.species_list.keys():
      logger.warning(f'Cannot construct URL for unknown species "{species_name}".')
      raise BadRequestError()

    # Get the desired template an fill in species information, if applicable
    t = Template(get_url_template(db_url_name))
    if species_name is not None:
      species = self.get_species(species_name)
      return t.substitute({
        'SPECIES': species_name,
        'PRJ':     species.proj_num,
        'WB':      species.wb_ver,
      })
    else:
      return t.template



## GS Blobs ##

def get_blob_template(db_url_name: str):
    '''
      Gets the blob template associated with a given template name.
        Args:
          db_url_name (str): [The name of the template to retrieve.]
        Returns:
          str: [The GS blob template associated with the given name.]
    '''
    blob_template = internal_db_blob_templates.get(db_url_name)
    if blob_template is None:
        logger.warning(f'Unrecognized blob template name "{db_url_name}".')
        raise BadRequestError()
    else:
        return Template(blob_template)


def get_blob(self, db_url_name: str, species_name: str):

    # Get the species object
    species = self.get_species(species_name)

    # Get the blob template
    t = get_blob_template(db_url_name)

    # Substitute in relevant species values
    return t.substitute({
        'SPECIES': species_name,
        'SVA':     species.sva_ver,
    })



## Filenames ##

def get_download_path(self, species_name: str = ''):
  if species_name == '':
    return self.local_download_path
  else:
    return f'{self.local_download_path}/{species_name}'


def get_file_suffix(self, db_url_name: str):

  # Get the URL template
  url = get_url_template(db_url_name)

  # Determine whether the URL is zipped
  is_zipped = url[-3:] == '.gz'

  # If URL is zipped, suffix is everything after the second-to-last period
  if is_zipped:
    suffix = url[ url[:-3].rfind('.') + 1 :]

  # Otherwise, suffix is everything after the final period
  else:
    suffix = url[ url.rfind('.') + 1 :]

  # Split the suffix into an array
  # First element will be the 'true' suffix, and if the file is zipped, second will be '.gz'
  return suffix.split('.')


def get_filename(self, db_url_name: str, species_name: str = ''):
    '''
      Gets the local filename for a URL template and species.  Does NOT guarantee that this file exists.
        Args:
          db_url_name (str): [The name of the template to retrieve.]
          species_name (str, optional): [The species to fill in the template with. Defaults to None. Optional, but must be provided for certain templates.]
        Returns:
          str: [The location in the local downloads folder where the downloaded file belongs.]
    '''

    # Get the path to the correct (sub)directory
    if (url_template_type(db_url_name) == 'generic'):
      download_path = self.get_download_path()
    else:
      download_path = self.get_download_path(species_name)

    # Compute file suffix, ignoring '.gz' if zipped
    suffix = self.get_file_suffix(db_url_name)[0]

    # Use URL name as filename in computed download path
    return f'{download_path}/{db_url_name}.{suffix}'
