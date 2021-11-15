from google.cloud import storage

storageClient = storage.Client()


def get_blob_list(bucket_name, prefix):
  ''' Returns a list of all blobs with 'prefix' (directory) in 'bucket_name' '''
  bucket = storageClient.get_bucket(bucket_name)
  items = bucket.list_blobs(prefix=prefix)
  return items

def generate_blob_url(bucket_name, blob_name):
  ''' Generates the public https URL for a blob '''
  return f"https://storage.googleapis.com/{bucket_name}/{blob_name}" 


def download_blob_to_file(bucket_name, blob_name, filename):
  ''' Downloads a blob and saves it locally '''   
  bucket = storageClient.get_bucket(bucket_name)
  blob = bucket.blob(blob_name)
  blob.download_to_file(open(filename, 'wb'))
  return filename
