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

from polaris.common import db
from polaris.common.enums import WorkTrackingIntegrationType
from polaris.utils.collections import dict_select
from polaris.utils.exceptions import IllegalArgumentError
from .model import WorkItemsSource, work_items, work_items_sources, WorkItem

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
                    work_item_type=work_item.work_item_type,
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
                ]).where(
                    work_items_sources.c.integration_type.in_([
                        WorkTrackingIntegrationType.github.value,
                        WorkTrackingIntegrationType.pivotal.value
                    ])
                )
            ).fetchall()
        ]


def get_parameters(work_items_source_input):
    integration_type = work_items_source_input['integration_type']
    if WorkTrackingIntegrationType.pivotal.value == integration_type:
        return work_items_source_input['pivotal_parameters']
    elif WorkTrackingIntegrationType.github.value == integration_type:
        return work_items_source_input['github_parameters']
    elif WorkTrackingIntegrationType.jira.value == integration_type:
        return work_items_source_input['jira_parameters']
    else:
        raise IllegalArgumentError(f"Unknown integration type {integration_type}")


def create_work_items_source(work_items_source_input, join_this=None):
    with db.orm_session(join_this) as session:
        session.expire_on_commit = False
        parameters = get_parameters(work_items_source_input)
        work_item_source = WorkItemsSource(
            key=work_items_source_input.get('key', uuid.uuid4().hex),
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


def insert_work_item(work_items_source_key, work_item_data, join_this=None):
    return sync_work_items(work_items_source_key, [work_item_data], join_this)[0]


def update_work_item(work_items_source_key, work_item_data, join_this=None):
    return sync_work_items(work_items_source_key, [work_item_data], join_this)[0]


def delete_work_item(work_items_source_key, work_item_data, join_this=None):
    with db.orm_session(join_this) as session:
        session.expire_on_commit = False
        work_items_source = WorkItemsSource.find_by_work_items_source_key(session, work_items_source_key)
        if work_items_source:
            work_item = WorkItem.findBySourceDisplayId(
                session, work_items_source.id,
                work_item_data.get('source_display_id')
            )
            if work_item:
                work_item.deleted_at = work_item_data['deleted_at']
                return dict(
                    is_delete=True,
                    key=work_item.key,
                    work_item_type=work_item.work_item_type,
                    display_id=work_item.source_display_id,
                    url=work_item.url,
                    name=work_item.name,
                    description=work_item.description,
                    is_bug=work_item.is_bug,
                    tags=work_item.tags,
                    state=work_item.source_state,
                    created_at=work_item.source_created_at,
                    updated_at=work_item.source_last_updated,
                    last_sync=work_item.last_sync,
                    deleted_at=work_item.deleted_at
                )


def sync_work_items_sources(connector, work_items_sources_list, join_this=None):
    if len(work_items_sources_list) > 0:
        with db.orm_session(join_this) as session:
            work_items_sources_temp = db.temp_table_from(
                work_items_sources,
                table_name='work_items_sources_temp',
                exclude_columns=[work_items_sources.c.id]
            )
            work_items_sources_temp.create(session.connection(), checkfirst=True)

            session.connection().execute(
                insert(work_items_sources_temp).values(
                    [
                        dict(
                            key=uuid.uuid4(),
                            connector_key=connector.key,
                            account_key=connector.account_key,
                            **work_items_source
                        )
                        for work_items_source in work_items_sources_list
                    ]
                )
            )

            work_items_sources_before_insert = session.connection().execute(
                select([*work_items_sources_temp.columns, work_items_sources.c.key.label('current_key')]).select_from(
                    work_items_sources_temp.outerjoin(
                        work_items_sources,
                        and_(
                            work_items_sources_temp.c.connector_key == work_items_sources.c.connector_key,
                            work_items_sources_temp.c.source_id == work_items_sources.c.source_id
                        )
                    )
                )
            ).fetchall()

            upsert = insert(work_items_sources).from_select(
                [column.name for column in work_items_sources_temp.columns],
                select([work_items_sources_temp])
            )

            session.connection().execute(
                upsert.on_conflict_do_update(
                    index_elements=['connector_key', 'source_id'],
                    set_=dict(
                        name=upsert.excluded.name,
                        description=upsert.excluded.description,
                        url=upsert.excluded.url,
                        source_record=upsert.excluded.source_record
                    )
                )
            )

            return [
                dict(
                    is_new=work_items_source.current_key is None,
                    key=work_items_source.key if work_items_source.current_key is None else work_items_source.current_key,
                    integration_type=work_items_source.integration_type,
                    source_id=work_items_source.source_id,
                    url=work_items_source.url,
                    name=work_items_source.name,
                    description=work_items_source.description
                )
                for work_items_source in work_items_sources_before_insert
            ]