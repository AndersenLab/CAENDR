# Base Class
from .job_pipeline import JobPipeline

# Subclasses
from .database_operation_pipeline import DatabaseOperationPipeline
from .indel_primer_pipeline       import IndelFinderPipeline
from .heritability_pipeline       import HeritabilityPipeline
from .nemascan_pipeline           import NemascanPipeline



# Collect the set of pipeline subclasses
pipelineSubclasses = { DatabaseOperationPipeline, IndelFinderPipeline, HeritabilityPipeline, NemascanPipeline }

# Ensure that all kind values are unique
# TODO: Can this be a unit test?
for cls_i in pipelineSubclasses:
  for cls_j in pipelineSubclasses:
    assert cls_i == cls_j or cls_i.get_kind() != cls_j.get_kind(), \
      f'JobPipeline subclasses {cls_i.__name__} and {cls_j.__name__} both have the kind {cls_i.get_kind()}'


def getJobPipelineClass(class_or_kind):

  # Determine the target kind, accepting both objects with a "kind" field and a straight kind itself
  try:
      target_kind = class_or_kind.kind
  except Exception:
    try:
      target_kind = class_or_kind.get_kind()
    except Exception:
      target_kind = class_or_kind

  # Loop through the set of JobPipeline subclasses, matching based on kind
  for cls in pipelineSubclasses:
    if cls.get_kind() == target_kind:
      return cls

  # If none matched, raise an error
  raise ValueError()
