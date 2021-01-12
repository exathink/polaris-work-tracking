# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal

import logging
from flask import Blueprint, request

logger = logging.getLogger('polaris.work_tracking.integrations.gitlab.webhook')

webhook = Blueprint('gitlab_webhooks', __name__)


@webhook.route(f"/project/webhooks/<connector_key>/", methods=('GET', 'POST'))
def project_webhooks(connector_key):
    pass
