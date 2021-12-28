locals {
  asset_path = abspath("${path.module}/../../../../src/modules/site/ext_assets")
  file_set = fileset(local.asset_path, "**")
  mime_types = {
    ".js": "text/javascript",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".mp4": "video/mp4",
    ".png": "image/png",
    ".gif": "image/gif",
    ".tsv": "text/tab-separated-values"
  }
}


resource "google_storage_bucket_object" "asset" {
  for_each = local.file_set

  name = each.key
  source = "${local.asset_path}/${each.value}"
  bucket = google_storage_bucket.static_assets.name
  content_type = lookup(local.mime_types, regex("\\.[^.]+$", each.key), null)

  depends_on = [
    google_storage_bucket_access_control.public_rule
  ]
}


resource "google_storage_object_access_control" "public_rule" {
  for_each = google_storage_bucket_object.asset

  object = each.value.output_name
  bucket = google_storage_bucket.static_assets.name
  role   = "READER"
  entity = "allUsers"
  depends_on = [
    google_storage_bucket_access_control.public_rule
  ]
}
