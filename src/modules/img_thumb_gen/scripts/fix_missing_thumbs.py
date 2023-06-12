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
  logger.info(f'Triggered by: bucket:{data["bucket"]}, name:{data["name"]}')
  thumbnail_regex = f"\.thumb.(jpg|jpeg)$"
  image_regex = f"\.(jpg|jpeg)$"

  # Only generate thumbnails for matching paths
  is_image = re.search(image_regex, data['name'])
  is_thumbnail = re.search(thumbnail_regex, data['name']) 

  if (is_image and not is_thumbnail):
    logger.info(f'Creating new thumbnail for image: {data}')
    # Download the image and resize it
    bucket = client.get_bucket(data['bucket'])
    thumbnail = Image(blob=bucket.get_blob(data['name']).download_as_string())
    thumbnail.transform(resize='x200')

    # Upload the thumbnail with modified name
    path = data['name'].rsplit('.', 1)
    blob_name = path[0] + ".thumb." + path[1]
    thumbnail_blob = bucket.blob(blob_name)
    thumbnail_blob.upload_from_string(thumbnail.make_blob())
    logger.info(f'Uploaded new thumbnail for image: {blob_name}')

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


print("hello")

if __name__ == '__main__':
  print("[Running script] fix_missing_thumbs ENV={ENV}")
#   run()