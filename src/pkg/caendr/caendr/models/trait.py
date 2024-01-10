from caendr.models.datastore import TraitFile



class Trait():
  '''
    Utility class for converting between different representations of the same trait:
      - Dataset + unique name
      - Datastore unique ID
      - SQL metadata row / value query

    Tracks a trait file, and if it's a bulk file, a unique trait name within that file.

    TODO: Ideally an intermediary like this wouldn't be necessary. Can we simplify trait representation?
  '''


  #
  # Initialization
  #

  def __init__(self, dataset = None, trait_name = None, trait_file_id = None, trait_file = None):
    self.name = trait_name

    # Trait file passed directly -- store it as-is
    if trait_file:
      self.file = trait_file

    # Trait file id -- retrieve from datastore
    elif trait_file_id:
      self.file = TraitFile.get_ds(trait_file_id)

    # Special case: Zhang bulk file -- retrieve to single bulk file entry
    # TODO: We might be able to generalize this if we enforce that every dataset has to either
    #       have a single bulk file (and nothing else), or some number of non-bulk files (and no bulk files).
    #       We could then query by dataset and check the output to determine what TraitFile to use.
    elif dataset == 'zhang':
      self.file = TraitFile.query_ds_unique('dataset', dataset, required=True)

    # Dataset -- query by name and dataset
    elif dataset:
      self.file = TraitFile.query_ds(filters=[('trait_name_caendr', '=', trait_name), ('dataset', '=', dataset)])[0]

    # Fallback -- Query by trait name
    elif trait_name:
      self.file = TraitFile.query_ds_unique('trait_name_caendr', trait_name, required=True)

    # If none of the above were provided, there's not enough info to uniquely specify the trait
    else:
      raise ValueError('Could not identify a unique trait from the given information')

    # Store the dataset value of the trait file
    if dataset and self.file['dataset'] and dataset != self.file['dataset']:
      raise ValueError('Mismatched dataset values')
    self.dataset = self.file['dataset']
