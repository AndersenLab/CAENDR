import pkg_resources
__version__ = pkg_resources.require("caendr")[0].version


from .utils.env import load_env
dotenv_file = '.env'
load_env(dotenv_file)
