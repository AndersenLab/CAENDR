from setuptools import setup

setup(
  name='caendr',
  version='0.0.1',
  packages=['caendr'],
  install_requires=[
    'cachelib',
    'Flask_SQLAlchemy==2.5.1',
    'Flask==1.1.2',
    'google-api-python-client',
    'google-cloud-tasks',
    'google-cloud-secret-manager',
    'google-cloud-storage',
    'google-cloud-datastore',
    'google_cloud_logging',
    'gspread==3.6.0',
    'logzero==1.3.1',
    'oauth2client',
    'pandas==1.0.5',
    'plotly==2.2.3',
    'python-dotenv==0.19.1',
    'importlib; python_version == "3.8.10"',
  ],
)
