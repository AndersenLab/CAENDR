locals {
  codebase_root_path = abspath("${path.module}/../../../../src/modules/img_thumb_gen")
  timestamp = formatdate("YYMMDDhhmmss", timestamp())
}

# Compress source code
data "archive_file" "source" {
  type        = "zip"
  source_dir  = local.codebase_root_path
  excludes    = [ ]
  output_path = "/tmp/function-${local.timestamp}.zip"
}

# Add source code zip to bucket
resource "google_storage_bucket_object" "source_zip" {
  # Append file MD5 to force bucket to be recreated
  name   = "source.zip#${data.archive_file.source.output_md5}"
  bucket = google_storage_bucket.source_bucket.name
  source = data.archive_file.source.output_path
}
