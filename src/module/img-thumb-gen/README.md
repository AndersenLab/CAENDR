# Generate Thumbnails
Google Cloud Function triggered by uploads to a specific cloud bucket (configured via terraform)
The path to monitor for uploads of high-res photos is configured by MODULE_IMG_THUMB_GEN_SOURCE_PATH environment variable from .env
Generated thumbnails have the form /img/photo.jpg -> /img/photo.thumb.jpg
Original images must have .jpg or .jpeg file extensions
