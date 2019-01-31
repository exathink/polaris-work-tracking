# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2017) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar
import sys
from flask_compress import Compress
import logging

from polaris.utils.config import get_config_provider
from polaris.flask.common import PolarisSecuredService

from polaris.flask import gql
from polaris.work_tracking.service import graphql

from polaris.utils.logging import config_logging

config_logging()


class PolarisWorkTrackingService(PolarisSecuredService):
    def __init__(self, import_name, db_url, db_connect_timeout=30, models=None,
                 public_paths=None, **kwargs):
        super(PolarisWorkTrackingService, self).__init__(
            import_name, db_url, db_connect_timeout,
            models=models,
            public_paths=public_paths,
            **kwargs
        )
        self.public_paths.extend([])


config_provider = get_config_provider()
app = PolarisWorkTrackingService(
    __name__,
    db_url=config_provider.get('POLARIS_DB_URL')
)

if config_provider.get('DEBUG_SQL') == 'true':
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Register endpoints
app.register_blueprint(gql.api, url_prefix='/graphql', schema=graphql.schema)


if app.env == 'production':
    app.config['COMPRESS_MIMETYPES'] = ['application/json', 'application/javascript']

    compress = Compress()
    compress.init_app(app)


# for dev mode use only.
if __name__ == "__main__":
    # Pycharm optimized settings.
    # Debug is turned off by default (use PyCharm debugger)
    # reloader is turned on by default so that we can get hot code reloading
    DEBUG = '--debug' in sys.argv
    RELOAD = '--no-reload' not in sys.argv
    app.run(host='0.0.0.0', port=8300, debug=DEBUG, use_reloader=RELOAD)