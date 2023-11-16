import os

from werkzeug.utils import secure_filename

from caendr.models.error import FileUploadError
from caendr.utils.data import unique_id



UPLOAD_DIR = os.path.join('.', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)


class LocalFile(os.PathLike):
  def __init__(self, local_file, valid_file_extensions=None):
    '''
      Temporarily upload a Flask `FileStorage` object to the server as a local file.
      Copies and validates the file extension of the uploaded file, if applicable.

      File is uploaded when entering this object's context (i.e. using a `with` block),
      and deleted when leaving the context.

      If more fine-grained control of the file lifecycle is required, the same can be
      achieved using the `create()` and `remove()` methods, respectively.
      In this case, the file will be deleted when this object is destroyed.

      This class inherits from `os.PathLike`, so standard file descriptor operations
      (in particular, `open()`) will work on the resulting object.

      Args:
        local_file(FileStorage):
          The FileStorage object to upload, e.g. from a Flask request.
        valid_file_extensions(iter(str), optional):
          A set of allowed file extensions. If filename does not have a valid extension,
          raises an error. If not provided, accepts any file extension.
    '''

    # Ensure the FileStorage object exists
    if not local_file:
      raise self._make_file_error()
    self.file = local_file

    # Match the file extension by splitting on right-most '.' character
    try:
      self.file_ext = self.file.filename.rsplit('.', 1)[1]
    except:
      self.file_ext = None

    # Validate file extension, if file_ext and valid_file_extensions are defined
    if self.file_ext and valid_file_extensions and (self.file_ext not in valid_file_extensions):
      raise self._make_file_error()

    # Create a unique local filename for the file
    # TODO: Is there a better way to generate this name?
    #       Using a Tempfile, using the user's ID and the time, etc.?
    self.target_filename = unique_id() + (f'.{self.file_ext}' if self.file_ext else '')


  #
  # Local Path
  #

  @property
  def local_path(self):
    return self.__local_path
  
  def __fspath__(self):
    return self.__local_path


  #
  # Creating (uploading) & removing the file from temporary storage
  #

  def create(self):
    '''
      Upload the file to local server storage temporarily.

      Return:
        local_path (str): The path of the file on the server.
    '''
    self.__local_path = os.path.join(UPLOAD_DIR, secure_filename(self.target_filename))
    try:
      self.file.save(self.__local_path)
    except Exception as ex:
      raise self._make_save_error() from ex
    return self

  def remove(self):
    '''
      Ensure the file is deleted from local server storage.

      Return:
        removed (bool): Whether the file existed.
    '''
    try:
      os.remove(self.__local_path)
      return True
    except FileNotFoundError:
      return False


  #
  # Map create and remove methods to __enter__ and __exit__, so we can use this class with a context manager
  #

  def __enter__(self):
    return self.create()

  def __exit__(self, type, value, traceback):
    self.remove()


  #
  # Map remove method to object destructor, to ensure temp file is removed when object is cleaned up
  #

  def __del__(self):
    self.remove()


  #
  # Errors
  #

  @staticmethod
  def _make_file_error():
    return FileUploadError(code=400)

  @staticmethod
  def _make_save_error():
    return FileUploadError(code=500)
