# Base class
# Everything else derives from this
from .entity              import Entity

# Basic data classes
from .container           import Container
from .user                import User
from .pipeline_operation  import PipelineOperation
from .wormbase            import WormbaseVersion, WormbaseProjectNumber
from .species             import Species, SPECIES_LIST # Imports WormbaseVersion, WormbaseProjectNumber

# Abstract template classes (add basic field(s) & functionality)
from .file_record_entity  import FileRecordEntity
from .hashable_entity     import HashableEntity
from .publishable_entity  import PublishableEntity
from .species_entity      import SpeciesEntity       # Imports Species
from .status_entity       import StatusEntity
from .user_owned_entity   import UserOwnedEntity     # Imports User

from .dataset_release     import DatasetRelease      # Subclasses SpeciesSpecificEntity; Imports Species

# Job template classes
from .job_entity          import JobEntity           # Subclasses StatusEntity; imports Container
from .report_entity       import ReportEntity        # Subclasses JobEntity, UserOwnedEntity, as well as GCPReport

# Jobs
from .database_operation  import DatabaseOperation   # Subclasses ReportEntity
from .gene_browser_tracks import GeneBrowserTracks   # Subclasses JobEntity  (DEPRECATED)
from .indel_primer        import IndelPrimerReport   # Subclasses ReportEntity, HashableEntity; imports DatasetRelease, Species
from .heritability_report import HeritabilityReport  # Subclasses ReportEntity, HashableEntity
from .nemascan_mapping    import NemascanReport      # Subclasses ReportEntity, HashableEntity

# Other
from .database_operation  import DbOp
from .profile             import Profile
from .markdown            import Markdown
from .browser_track       import BrowserTrackDefault  # Subclasses FileRecordEntity (from BrowserTrack)
from .browser_track       import BrowserTrackTemplate # Subclasses FileRecordEntity (from BrowserTrack)
from .trait_file          import TraitFile            # Subclasses FileRecordEntity, PublishableEntity, SpeciesEntity, UserOwnedEntity


def get_class_by_kind(kind):
  '''
    Get the Entity subclass that corresponds with the given kind.

    Arguments:
      - kind: The kind of the entity.

    Returns:
      The Entity subclass.

    Raises:
      ValueError: Provided kind is not valid.
  '''

  KIND_MAPPING = {
    Container.kind:          Container,
    User.kind:               User,
    DatasetRelease.kind:     DatasetRelease,
    Profile.kind:            Profile,
    PipelineOperation.kind:  PipelineOperation,

    DatabaseOperation.kind:  DatabaseOperation,
    IndelPrimerReport.kind:  IndelPrimerReport,
    HeritabilityReport.kind: HeritabilityReport,
    NemascanReport.kind:     NemascanReport,

    GeneBrowserTracks.kind:  GeneBrowserTracks,
    Markdown.kind:           Markdown,
    Species.kind:            Species,
  }

  try:
    return KIND_MAPPING[kind]
  except:
    raise ValueError(f"Unrecognized kind: {kind}")


def get_entity_by_kind(kind, name):
  '''
    Get the entity with the given kind & name, cast to the appropriate subclass.

    Arguments:
      - kind: The kind of the entity.
      - name: The name of the entity (unique within the given kind).

    Returns:
      An Entity subclass object representing the desired entity.

    Raises:
      ValueError: Provided kind is not valid.
      NotFoundError: No entity with the given name + kind exists.
  '''
  return get_class_by_kind(kind).get_ds(name, silent=False)
