module "img_thumb_gen" {
  source = "./modules/img-thumb-gen"
  ENVIRONMENT = var.ENVIRONMENT

  google_cloud_vars = local.google_cloud_vars
  bucket_photos_name = var.MODULE_SITE_BUCKET_PHOTOS_NAME
  image_source_path = var.MODULE_IMG_THUMB_GEN_SOURCE_PATH
  
  depends_on = [
    null_resource.api_service_group_all
  ]
}


module "ext_assets" {
  source = "./modules/ext_assets"
  ENVIRONMENT = var.ENVIRONMENT

  bucket_assets_name = var.MODULE_SITE_BUCKET_ASSETS_NAME
  google_cloud_vars = local.google_cloud_vars

  asset_versioning = true

  depends_on = [
    null_resource.api_service_group_all
  ]
}



module "site" {
  source = "./modules/site"
  ENVIRONMENT = var.ENVIRONMENT

  google_cloud_vars = local.google_cloud_vars
  module_site_vars = local.module_site_vars
  cloud_secret_vars = local.cloud_secret_vars

  depends_on = [
    module.ext_assets,
    module.img_thumb_gen,
    null_resource.api_service_group_all
  ]
}

