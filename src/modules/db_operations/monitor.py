# sentry
import os
import sentry_sdk

def init_sentry():
    SENTRY_URL = os.getenv('SENTRY_URL')
    if SENTRY_URL is None:
        return
    try:
        env = os.getenv("ENV")
        sentry_sdk.init(
            SENTRY_URL,
            environment = f"db_operations-{env}",
            # Set traces_sample_rate to 1.0 to capture 100%
            # of transactions for performance monitoring.
            # We recommend adjusting this value in production.
            traces_sample_rate=1.0
        )
    except:
        pass
