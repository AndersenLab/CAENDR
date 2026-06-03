locals {
  codebase_root_path = abspath("${path.module}/../../../../src/modules/img_thumb_gen")
  timestamp = formatdate("YYMMDDhhmmss", timestamp())
}

resource "null_resource" "configure_img_thumb_gen" {
  triggers = tomap({
    "rebuild": true
  })

  provisioner "local-exec" {
    command = format("make -C %s clean clean-venv dot-env ENV=%s", local.codebase_root_path, var.ENVIRONMENT)
  }
}

# Compress source code
data "archive_file" "source" {
  type        = "zip"
  source_dir  = local.codebase_root_path
  excludes    = [ ]
  output_path = "/tmp/function-${local.timestamp}.zip"

  depends_on = [
    null_resource.configure_img_thumb_gen
  ]
}

# Add source code zip to bucket
resource "google_storage_bucket_object" "source_zip" {
  # Append file MD5 to force bucket to be recreated
  # name   = "source.zip#${data.archive_file.source.output_md5}"
  name   = "source.${data.archive_file.source.output_md5}.zip"
  bucket = google_storage_bucket.source_bucket.name
  source = data.archive_file.source.output_path
  content_type = "application/zip"

  depends_on = [
    data.archive_file.source
  ]
}
