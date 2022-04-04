# Image Thumbnail Generator

## src/modules/img_thumb_gen
-------------------------------------------------------------------
This module runs as a Google Cloud Function which is triggered by completed uploads to a target cloud bucket (configured by terraform)

Thumbnails are only created for jpeg images uploaded to the bucket and path defined in MODULE_SITE_BUCKET_PHOTOS_NAME and MODULE_IMG_THUMB_GEN_SOURCE_PATH, respectively. These environment variables are loaded from the global.env file for the current environment.

Original images must have .jpg or .jpeg file extensions

example:

MODULE_SITE_BUCKET_PHOTOS_NAME=public-image-bucket
MODULE_IMG_THUMB_GEN_SOURCE_PATH=img/subdir

public-image-bucket/img/subdir/photo.jpg -> public-image-bucket/img/subdir/photo.thumb.jpg


