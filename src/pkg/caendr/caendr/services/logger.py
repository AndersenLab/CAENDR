from logzero import logger

try: 
    import google.cloud.logging
    client = google.cloud.logger.Client()
    client.setup_logger()
except:
    logger.info("not running inside GCP")
