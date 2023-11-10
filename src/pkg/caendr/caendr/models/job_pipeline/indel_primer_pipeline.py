import json
import numpy as np

# Parent Class & Models
from .job_pipeline                 import JobPipeline
from caendr.models.datastore       import IndelPrimerReport
from caendr.models.run             import GCPCloudRunRunner
from caendr.models.task            import IndelPrimerTask

# Services
from caendr.models.datastore       import Species
from caendr.models.error           import EmptyReportDataError, EmptyReportResultsError
from caendr.models.status          import JobStatus
from caendr.services.cloud.storage import download_blob_as_json, download_blob_as_dataframe, BlobURISchema
from caendr.utils.data             import get_object_hash
from caendr.utils.env              import get_env_var


INDEL_PRIMER_CONTAINER_NAME = get_env_var('INDEL_PRIMER_CONTAINER_NAME')



class IndelFinderPipeline(JobPipeline):

  #
  # Class variable assignments
  #

  # Managed class type assignments
  _Report_Class = IndelPrimerReport
  _Task_Class   = IndelPrimerTask
  _Runner_Class = GCPCloudRunRunner

  # Type declarations for managed objects
  # This clues the type checker in to the specific subclasses we're using in this JobPipeline subclass
  report: _Report_Class
  runner: _Runner_Class

  _Container_Name = INDEL_PRIMER_CONTAINER_NAME


  #
  # Parsing Submission
  #

  @classmethod
  def parse(cls, data, valid_file_extensions=None):
    data_file = json.dumps(data)
    data_hash = get_object_hash(data, length=32)

    # TODO: Pull this value from somewhere
    release = Species.from_name( data['species'] ).release_pif

    # Add release information to data object
    data.update({
      'release':         release,
      'sv_bed_filename': IndelPrimerReport.get_source_filename(data['species'], release) + '.bed.gz',
      'sv_vcf_filename': IndelPrimerReport.get_source_filename(data['species'], release) + '.vcf.gz',
    })

    return {
      'props': data,
      'hash':  data_hash,
      'files': [data_file],
    }



  #
  # Fetching & Parsing Input
  #

  def _parse_input(self, blob):

    data = download_blob_as_json(blob)

    # If data file is empty, raise an error
    if data is None or not bool(data):
      raise EmptyReportDataError(self.report.id)

    return data



  #
  # Fetching & Parsing Output
  #


  def fetch_output(self, raw: bool = False):
    result = super().fetch_output(raw=raw)

    # If result exists and report status hasn't been marked as finished yet, update it
    if result is not None and not self.is_finished():
      self.report.set_status( JobStatus.COMPLETE )
      self.report.save()

    # Return the result
    return result


  def _parse_output(self, blob):

    # Download results
    result = download_blob_as_dataframe(blob)

    # If file exists but there are no results, raise an error
    if result is None:
      raise EmptyReportResultsError(self.report.id)

    # If file exists and is empty, nothing??
    if result.empty:
      return {
        'empty': True,
      }

    # Left primer
    result['left_primer_start'] = result.amplicon_region.apply(lambda x: x.split(":")[1].split("-")[0]).astype(int)
    result['left_primer_stop']  = result.apply(lambda x: len(x['primer_left']) + x['left_primer_start'], axis=1)

    # Right primer
    result['right_primer_stop']  = result.amplicon_region.apply(lambda x: x.split(":")[1].split("-")[1]).astype(int)
    result['right_primer_start'] = result.apply(lambda x:  x['right_primer_stop'] - len(x['primer_right']), axis=1)

    # Output left and right melting temperatures.
    result[["left_melting_temp", "right_melting_temp"]] = result["melting_temperature"].str.split(",", expand = True)

    # REF Strain and ALT Strain
    ref_strain = result['0/0'].unique()[0]
    alt_strain = result['1/1'].unique()[0]

    # Extract chromosome and amplicon start/stop
    result[[None, "amp_start", "amp_stop"]] = result.amplicon_region.str.split(pat=":|-", expand=True)

    # Convert types
    result.amp_start = result.amp_start.astype(int)
    result.amp_stop  = result.amp_stop.astype(int)

    result["N"] = np.arange(len(result)) + 1

    # Associate table column names with the corresponding fields in the result objects
    columns = [

      # Basic Info
      ("Primer Set", "N"),
      ("Chrom", "CHROM"),

      # Left Primer
      ("Left Primer (LP)", "primer_left"),
      ("LP Start",         "left_primer_start"),
      ("LP Stop",          "left_primer_stop"),
      ("LP Melting Temp",  "left_melting_temp"),

      # Right Primer
      ("Right Primer (RP)", "primer_right"),
      ("RP Start",          "right_primer_start"),
      ("RP Stop",           "right_primer_stop"),
      ("RP Melting Temp",   "right_melting_temp"),

      # Amplicon
      (f"{ref_strain} (REF) amplicon size", "REF_product_size"),
      (f"{alt_strain} (ALT) amplicon size", "ALT_product_size"),
    ]

    # Convert list of (name, field) tuples to list of names and list of fields
    column_names, column_fields = zip(*columns)

    # Create table from results & columns
    format_table = result[list(column_fields)]
    format_table.columns = column_names

    return {
      'empty':        False,
      'dataframe':    result,
      'format_table': format_table,
    }



  #
  # Run Configuration
  #

  def construct_command(self):
    return ['python', '/indel_primer/main.py']

  def construct_environment(self):
    result_bucket, result_blob = self.report.output_filepath(schema=BlobURISchema.PATH)
    return {
      **super().construct_environment(),
      'RELEASE':        self.report['release'],
      'SPECIES':        self.report['species'],
      'INDEL_STRAIN_1': self.report['strain_1'],
      'INDEL_STRAIN_2': self.report['strain_2'],
      'INDEL_SITE':     self.report['site'],
      'RESULT_BUCKET':  result_bucket,
      'RESULT_BLOB':    result_blob,
    }

  def construct_run_params(self):
    return {
      **super().construct_run_params(),
      'BOOT_DISK_SIZE_GB': 20,
      'TIMEOUT':           '3600s',
    }