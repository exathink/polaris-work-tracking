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
from polaris.work_tracking.work_tracker import sync_work_items as api_import_work_items

from polaris.common import db

logger = logging.getLogger('polaris.work_tracking.cli')
token_provider = get_token_provider()

def import_work_items(work_items_source_key):
    result = api_import_work_items(token_provider, work_items_source_key)
    if result['total'] > 0:
        logger.log(logging.INFO, f"{len(result['created'])} new work items created")
        logger.log(logging.INFO, f"{result['updated']} work items updated")
    else:
        logger.log(logging.INFO, f"No updates found for work items source {work_items_source_key}")


if __name__ == '__main__':
    config_logging(
        suppress=['requests.packages.urllib3.connectionpool']
    )
    db.init()

    argh.dispatch_commands([
        import_work_items
    ])



