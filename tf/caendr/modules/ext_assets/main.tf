locals {
  asset_path = abspath("${path.module}/../../../../src/modules/site/ext_assets")
  file_set = fileset(local.asset_path, "**")
}


resource "google_storage_bucket_object" "asset" {
  for_each = local.file_set

  name = each.key
  source = "${local.asset_path}/${each.value}"
  bucket = google_storage_bucket.static_assets.name
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
