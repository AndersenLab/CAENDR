# Parent classes
from .runner import Runner, GCPRunner, GCPCloudRunRunner, GCPLifesciencesRunner
from .local  import LocalRunner

# Job-specific subclasses
from .tools_gcp_cloudrun import DatabaseOperationRunner, IndelPrimerRunner, HeritabilityRunner, NemascanRunner
