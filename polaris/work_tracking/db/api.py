# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import uuid
import logging
from polaris.common import db
from .model import WorkItem, WorkItemsSource

logger = logging.getLogger('polaris.work_tracker.db.api')

def import_work_items(work_items_source_key, work_items, join_this=None):
    with db.orm_session(join_this)as session:
        work_items_source = WorkItemsSource.find_by_work_items_source_key(session, work_items_source_key)
        for work_item in work_items:
            session.add(
                WorkItem(
                    key=uuid.uuid4(),
                    work_items_source=work_items_source,
                    **work_item
                )
            )
    if len(work_items) > 0:
        logger.info(f'Imported {len(work_items)} work items')
    return len(work_items)
