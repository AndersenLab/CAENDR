from importlib.metadata import version
__version__ = version("caendr")


from .utils.env import load_env
dotenv_file = '.env'
load_env(dotenv_file)
