from .entity              import Entity
from .container           import Container
from .user                import User
from .job_entity          import JobEntity
from .user_owned_entity   import UserOwnedEntity
from .data_job_entity     import DataJobEntity
from .dataset_release     import DatasetRelease
from .profile             import Profile
from .nemascan_mapping    import NemascanMapping
from .pipeline_operation  import PipelineOperation
from .database_operation  import DatabaseOperation
from .indel_primer        import IndelPrimer
from .heritability_report import HeritabilityReport
from .gene_browser_tracks import GeneBrowserTracks
from .markdown            import Markdown
from .wormbase            import WormbaseVersion, WormbaseProjectNumber
from .species             import Species, SPECIES_LIST


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

  KIND_MAPPING = {
    Container.kind:          Container,
    User.kind:               User,
    DatasetRelease.kind:     DatasetRelease,
    Profile.kind:            Profile,
    PipelineOperation.kind:  PipelineOperation,

    DatabaseOperation.kind:  DatabaseOperation,
    IndelPrimer.kind:        IndelPrimer,
    HeritabilityReport.kind: HeritabilityReport,
    NemascanMapping.kind:    NemascanMapping,

    GeneBrowserTracks.kind:  GeneBrowserTracks,
    Markdown.kind:           Markdown,
    Species.kind:            Species,
  }

  try:
    cls = KIND_MAPPING[kind]
  except:
    raise ValueError(f"Unrecognized kind: {kind}")

  return cls.get_ds(name, silent=False)
