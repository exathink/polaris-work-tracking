# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from polaris.common import db
from polaris.work_tracking.db.model import WorkItemsSource

def find_work_items(work_items_source_key, source_ids):
    with db.orm_session() as session:
        return WorkItemsSource.find_by_key(
            session, work_items_source_key
        ).find_work_items_by_source_id(
            session, source_ids
        )