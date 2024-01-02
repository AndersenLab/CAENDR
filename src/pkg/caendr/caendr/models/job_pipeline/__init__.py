from typing import Type

# Base Class
from .job_pipeline import JobPipeline

# Subclasses
from .database_operation_pipeline import DatabaseOperationPipeline
from .indel_primer_pipeline       import IndelFinderPipeline
from .heritability_pipeline       import HeritabilityPipeline
from .nemascan_pipeline           import NemascanPipeline
from .phenotype_pipeline          import PhenotypePipeline



# Collect the set of pipeline subclasses
pipeline_subclasses = frozenset({ DatabaseOperationPipeline, IndelFinderPipeline, HeritabilityPipeline, NemascanPipeline, PhenotypePipeline })

# Ensure that all kind values are unique
# TODO: Can this be a unit test?
for cls_i in pipeline_subclasses:
  for cls_j in pipeline_subclasses:
    assert cls_i == cls_j or cls_i.get_kind() != cls_j.get_kind(), \
      f'JobPipeline subclasses {cls_i.__name__} and {cls_j.__name__} both have the kind {cls_i.get_kind()}'



def get_pipeline_class(kind = None, queue: str = None) -> Type[JobPipeline]:
  '''
    Get the appropriate JobPipeline subclass using *either* the kind or the queue name.

    Kind is defined by the associated Report (storage) class.
    Queue name is defined by the Task (scheduler) class.
  '''

  # Make arguments mutually exclusive
  if not ((kind is None) ^ (queue is None)):
    raise ValueError('Exactly one of "kind" and "queue" should be provided when looking up JobPipeline subclass.')


  # Lookup by queue name #

  if queue is not None:

    # Loop through the set of JobPipeline subclasses, matching based on queue name
    for cls in pipeline_subclasses:
      if cls.get_queue() == queue:
        return cls

    # If none matched, raise an error
    raise ValueError()


  # Lookup by kind #

  # Determine the target kind, accepting both objects with a "kind" field and a straight kind itself
  try:
      target_kind = kind.kind
  except Exception:
    try:
      target_kind = kind.get_kind()
    except Exception:
      target_kind = kind

  # Loop through the set of JobPipeline subclasses, matching based on kind
  for cls in pipeline_subclasses:
    if cls.get_kind() == target_kind:
      return cls

  # If none matched, raise an error
  raise ValueError()
