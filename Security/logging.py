import os
import logging

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


def init_sentry():
    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR,
    )

    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        integrations=[
            FlaskIntegration(),
            sentry_logging,
        ],
        send_default_pii=False,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.0,
        environment=os.getenv("FLASK_ENV", "production"),
        debug=False,
    )