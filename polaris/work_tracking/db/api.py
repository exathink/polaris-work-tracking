# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging
import uuid
from datetime import datetime

from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert
from polaris.utils.collections import dict_select
from polaris.utils.exceptions import IllegalArgumentError

from polaris.common import db
from .model import WorkItemsSource, work_items, work_items_sources
from polaris.common.enums import WorkTrackingIntegrationType

logger = logging.getLogger('polaris.work_tracker.db.api')


def sync_work_items(work_items_source_key, work_item_list, join_this=None):
    if len(work_item_list) > 0:
        with db.orm_session(join_this) as session:
            work_items_source = WorkItemsSource.find_by_work_items_source_key(session, work_items_source_key)
            work_items_temp = db.temp_table_from(
                work_items,
                table_name='work_items_temp',
                exclude_columns=[work_items.c.id]
            )
            work_items_temp.create(session.connection(), checkfirst=True)

            last_sync = datetime.utcnow()
            session.connection().execute(
                insert(work_items_temp).values(
                    [
                        dict(
                            key=uuid.uuid4(),
                            work_items_source_id=work_items_source.id,
                            last_sync=last_sync,
                            **work_item
                        )
                        for work_item in work_item_list
                    ]
                )
            )

            work_items_before_insert = session.connection().execute(
                select([*work_items_temp.columns, work_items.c.key.label('current_key')]).select_from(
                    work_items_temp.outerjoin(
                        work_items,
                        and_(
                            work_items_temp.c.work_items_source_id == work_items.c.work_items_source_id,
                            work_items_temp.c.source_id == work_items.c.source_id
                        )
                    )
                )
            ).fetchall()

            upsert = insert(work_items).from_select(
                [column.name for column in work_items_temp.columns],
                select([work_items_temp])
            )

            session.connection().execute(
                upsert.on_conflict_do_update(
                    index_elements=['work_items_source_id', 'source_id'],
                    set_=dict(
                        name=upsert.excluded.name,
                        description=upsert.excluded.description,
                        is_bug=upsert.excluded.is_bug,
                        tags=upsert.excluded.tags,
                        url=upsert.excluded.url,
                        source_last_updated=upsert.excluded.source_last_updated,
                        source_display_id=upsert.excluded.source_display_id,
                        source_state=upsert.excluded.source_state,
                        last_sync=upsert.excluded.last_sync
                    )
                )
            )

            return [
                dict(
                    is_new=work_item.current_key is None,
                    key=work_item.key if work_item.current_key is None else work_item.current_key,
                    integration_type=work_items_source.integration_type,
                    display_id=work_item.source_display_id,
                    url=work_item.url,
                    name=work_item.name,
                    description=work_item.description,
                    is_bug=work_item.is_bug,
                    tags=work_item.tags,
                    state=work_item.source_state,
                    created_at=work_item.source_created_at,
                    updated_at=work_item.source_last_updated,
                    last_sync=work_item.last_sync
                )
                for work_item in work_items_before_insert
            ]


def resolve_work_items_by_display_ids(organization_key, display_ids):
    resolved = {}
    if len(display_ids) > 0:
        with db.create_session() as session:
            resolved = {
                work_item['display_id']: dict(
                    integration_type=work_item.integration_type,
                    work_item_key=work_item.key,
                    display_id=work_item.display_id,
                    url=work_item.url,
                    name=work_item.name,
                    is_bug=work_item.is_bug,
                    tags=work_item.tags,
                    created_at=work_item.source_created_at,
                    updated_at=work_item.source_last_updated,
                    last_sync=work_item.last_sync
                )
                for work_item in session.connection.execute(
                select([
                    work_items.c.key,
                    work_items.c.source_display_id.label('display_id'),
                    work_items.c.url,
                    work_items.c.name,
                    work_items.c.is_bug,
                    work_items.c.tags,
                    work_items.c.source_created_at,
                    work_items.c.source_last_updated,
                    work_items.c.last_sync,
                    work_items_sources.c.integration_type
                ]).select_from(
                    work_items.join(work_items_sources, work_items.c.work_items_source_id == work_items_sources.c.id)
                ).where(
                    and_(
                        work_items_sources.c.organization_key == organization_key,
                        work_items.c.source_display_id.in_(display_ids)
                    )
                )
            ).fetchall()
            }

    return resolved


def get_work_items_sources_to_sync():
    with db.create_session() as session:
        return [
            dict(
                organization_key=row.organization_key,
                work_items_source_key=row.key,
            )
            for row in session.connection.execute(
                select([
                    work_items_sources.c.key,
                    work_items_sources.c.organization_key
                ])
            ).fetchall()
        ]


def get_parameters(work_items_source_input):
    integration_type = work_items_source_input['integration_type']
    if WorkTrackingIntegrationType.pivotal.value == integration_type:
        return work_items_source_input['pivotal_parameters']
    elif WorkTrackingIntegrationType.github.value == integration_type:
        return work_items_source_input['github_parameters']
    else:
        raise IllegalArgumentError(f"Unknown integration type {integration_type}")


def create_work_items_source(work_items_source_input):
    with db.orm_session() as session:
        session.expire_on_commit = False
        parameters = get_parameters(work_items_source_input)
        work_item_source = WorkItemsSource(
            key=work_items_source_input.get('key', uuid.uuid4()),
            work_items_source_type=parameters['work_items_source_type'],
            parameters=parameters,
            **dict_select(work_items_source_input, [
                'name',
                'description',
                'integration_type',
                'account_key',
                'organization_key',
                'commit_mapping_scope',
                'commit_mapping_scope_key'
            ])
        )
        session.add(work_item_source)
        return work_item_source
