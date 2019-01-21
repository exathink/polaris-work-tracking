# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging
import argh
from polaris.utils.token_provider import get_token_provider
from polaris.utils.logging import config_logging

from polaris.messaging.utils import publish
from polaris.messaging.topics import WorkItemsTopic
from polaris.messaging.messages import ImportWorkItems



logger = logging.getLogger('polaris.work_tracking.cli')
token_provider = get_token_provider()


def import_work_items(work_items_source_key):
    publish(WorkItemsTopic, ImportWorkItems(send=dict(work_items_source_key=work_items_source_key)))


if __name__ == '__main__':
    config_logging(
        suppress=['requests.packages.urllib3.connectionpool']
    )


    argh.dispatch_commands([
        import_work_items
    ])



