# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import uuid
import logging
from polaris.common import db
from .model import WorkItem, WorkItemsSource, work_items
from sqlalchemy import select, and_, literal_column
from sqlalchemy.dialects.postgresql import insert

logger = logging.getLogger('polaris.work_tracker.db.api')


def sync_work_items(work_items_source_key, work_item_list, join_this=None):
    rows = 0
    if len(work_item_list) > 0:
        with db.orm_session(join_this) as session:
            work_items_source = WorkItemsSource.find_by_work_items_source_key(session, work_items_source_key)
            work_items_temp = db.temp_table_from(
                work_items,
                table_name='work_items_temp',
                exclude_columns=[work_items.c.id]
            )
            work_items_temp.create(session.connection(), checkfirst=True)

            upsert = insert(work_items).values([
                dict(
                    key=uuid.uuid4(),
                    work_items_source_id=work_items_source.id,
                    **work_item
                )
                for work_item in work_item_list
            ]
            )

            rows = session.connection().execute(
                upsert.on_conflict_do_update(
                    index_elements=['work_items_source_id','source_id'],
                    set_=dict(
                        name=upsert.excluded.name,
                        description=upsert.excluded.description,
                        is_bug=upsert.excluded.is_bug,
                        tags=upsert.excluded.tags,
                        url=upsert.excluded.url,
                        source_last_updated=upsert.excluded.source_last_updated,
                        source_display_id=upsert.excluded.source_display_id,
                        source_state=upsert.excluded.source_state
                    )
                )
            ).rowcount

    return rows
