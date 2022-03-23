# sentry
import os
import sentry_sdk
from logzero import logger


def init_sentry():
    SENTRY_URL = os.getenv('SENTRY_URL')
    if SENTRY_URL is None:
        return
    try:
        sentry_sdk.init(
            SENTRY_URL,
            environment=f"site-{os.getenv('ENV')}",
            # Set traces_sample_rate to 1.0 to capture 100%
            # of transactions for performance monitoring.
            # We recommend adjusting this value in production.
            traces_sample_rate=1.0
        )
    except Exception as e:
        logger.error(e)
        pass
