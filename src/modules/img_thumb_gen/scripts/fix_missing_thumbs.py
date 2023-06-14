import os
import re
import time

from logzero import logger
from wand.image import Image
from google.cloud import storage
from dotenv import load_dotenv

dotenv_file = '.env'
load_dotenv(dotenv_file)


# import monitor
# monitor.init_sentry("img_thumb_gen")

client = storage.Client()

ENV = os.environ.get("ENV")
if ENV is None:
    raise Exception("Missing ENV")
  

def generate_thumbnails(data, context):
  # Check if the file format is correct
  if not data['name'].lower().endswith(('jpg', 'jpeg')):
    raise Exception(f"{data['name']} is wrong file format. Thumbnails are generated only for .jpg or .jpeg files")

  logger.info(f'Triggered by: bucket:{data["bucket"]}, name:{data["name"]}')
  thumbnail_regex = f"\.thumb.(jpg|jpeg)$"
  image_regex = f"\.(jpg|jpeg)$"

  # Only generate thumbnails for matching paths
  is_image = re.search(image_regex, data['name'], re.IGNORECASE)
  is_thumbnail = re.search(thumbnail_regex, data['name'], re.IGNORECASE) 

  if (is_image and not is_thumbnail):
    logger.info(f'Creating new thumbnail for image: {data}')
    # Download the image and resize it
    bucket = client.get_bucket(data['bucket'])
    thumbnail = Image(blob=bucket.get_blob(data['name']).download_as_string())
    thumbnail.transform(resize='x200')

    # Upload the thumbnail with modified name
    filename, extension = data['name'].rsplit('.', 1)
    blob_name = filename + ".thumb." + extension.lower()
    thumbnail_blob = bucket.blob(blob_name)
    thumbnail_blob.upload_from_string(thumbnail.make_blob())
    logger.info(f'Uploaded new thumbnail for image: {blob_name}, {thumbnail_blob}')

  else:
    logger.info(f'Triggered but will not create thumbnail: is_image:{is_image} is_thumbnail:{is_thumbnail}')


def run():
    source_path = os.environ.get('MODULE_IMG_THUMB_GEN_SOURCE_PATH', None)
    if source_path is None:
        raise Exception("Missing MODULE_IMG_THUMB_GEN_SOURCE_PATH")

    if source_path.endswith('/'):
        source_path = source_path[:-1]
    if source_path.startswith('/'):
        source_path = source_path[1:]

    prefix = '^' + source_path.replace('/','\/') + '\/.*'


def run():
  GOOGLE_APPLICATION_CREDENTIALS=os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
  print(f"[Running script] fix_missing_thumbs ENV={ENV} GOOGLE_APPLICATION_CREDENTIALS={GOOGLE_APPLICATION_CREDENTIALS}")

  MODULE_SITE_BUCKET_PHOTOS_NAME = os.environ.get("MODULE_SITE_BUCKET_PHOTOS_NAME")
  if MODULE_SITE_BUCKET_PHOTOS_NAME is None:
    raise Exception("Missing MODULE_SITE_BUCKET_PHOTOS_NAME")
  bucket = client.get_bucket(MODULE_SITE_BUCKET_PHOTOS_NAME)

  files = list(bucket.list_blobs())
  filtered_files = [ file for file in files if file.name.startswith("c_") ]
  sorted_files = {}
  for file in filtered_files:
     end_idx = file.name.find('.')
     if end_idx == -1 or not file.name.lower().endswith(('jpg', 'jpeg')):
        print('wrong format file', file.name)
        continue
     sliced_name = file.name[0:end_idx]
     
     if sliced_name not in sorted_files:
      sorted_files[sliced_name] = [file]
     else:
      sorted_files.get(sliced_name).append(file)
  no_thumb_imgs = [files[0] for files in sorted_files.values() if len(files) == 1]
  for file in no_thumb_imgs:
    data = {
    "name" : file.name,
    "bucket" : MODULE_SITE_BUCKET_PHOTOS_NAME
    }
    context = {}
    generate_thumbnails(data, context)
  
    
  # EXAMPLE: pick a random file and create a thumb
  #target_file = "c_briggsae/MY2049.jpg"
  #data = {
  #   "name" : target_file,
  #   "bucket" : MODULE_SITE_BUCKET_PHOTOS_NAME
  #}
  #context = {}
  #generate_thumbnails(data, context)
  # run()


if __name__ == '__main__':
  run()

