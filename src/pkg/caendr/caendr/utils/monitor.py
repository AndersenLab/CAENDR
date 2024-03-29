# sentry
import os
import sys
import sentry_sdk
from caendr.services.logger import logger

def running_local():
    return sys.platform == 'darwin'

# Sentry has a single project for CAENDR. 
# Each component@env is a represented in Sentry as a unique environment
# Example:
# site@main, site@qa, site@dev, etl_operations@main, etc
#
# Parameters
# string @prefix - prefix for the sentry environment. 
def init_sentry(prefix = 'caendr', env = os.getenv('ENV', 'n/a')):

    # Check if running locally, and skip initializing Sentry if so
    if running_local():
        logger.info("Running locally - not initializing Sentry.")
        return

    # Try getting Sentry URL, and bail out if not defined
    SENTRY_URL = os.getenv('SENTRY_URL', None)
    if SENTRY_URL is None:
        logger.warn("E_SENTRY_INIT_MISSING_URL")
        return

    try:
        sentry_sdk.init(
            SENTRY_URL,
            environment = f"{prefix}@{env}",
            # Set traces_sample_rate to 1.0 to capture 100%
            # of transactions for performance monitoring.
            # We recommend adjusting this value in production.
            traces_sample_rate=1.0
        )
    except:
        pass
