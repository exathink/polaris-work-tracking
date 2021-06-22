# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging
import uuid
from datetime import datetime
from polaris.utils.collections import dict_drop
from sqlalchemy import select, and_, func, literal, Column, Integer
from sqlalchemy.dialects.postgresql import insert, UUID
from sqlalchemy.exc import SQLAlchemyError

from polaris.common import db
from polaris.common.enums import WorkTrackingIntegrationType, WorkItemsSourceImportState
from polaris.utils.collections import dict_select
from polaris.utils.exceptions import IllegalArgumentError, ProcessingException
from .model import WorkItemsSource, work_items, work_items_sources, WorkItem, Project

logger = logging.getLogger('polaris.work_tracker.db.api')


def sync_work_items(work_items_source_key, work_item_list, join_this=None):
    if len(work_item_list) > 0:
        with db.orm_session(join_this) as session:
            work_items_source = WorkItemsSource.find_by_key(session, work_items_source_key)
            work_items_temp = db.temp_table_from(
                work_items,
                table_name='work_items_temp',
                exclude_columns=[work_items.c.id, work_items.c.parent_id]
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

            parent_work_items = work_items.alias('parent_work_items')
            work_items_before_insert = session.connection().execute(
                select([*work_items_temp.columns, work_items.c.key.label('current_key'),
                        parent_work_items.c.key.label('parent_key')]).select_from(
                    work_items_temp.outerjoin(
                        work_items,
                        and_(
                            work_items_temp.c.work_items_source_id == work_items.c.work_items_source_id,
                            work_items_temp.c.source_id == work_items.c.source_id
                        )
                    ).outerjoin(
                        parent_work_items,
                        and_(
                            parent_work_items.c.work_items_source_id == work_items.c.work_items_source_id,
                            parent_work_items.c.id == work_items.c.parent_id
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
                        is_epic=upsert.excluded.is_epic,
                        work_item_type=upsert.excluded.work_item_type,
                        tags=upsert.excluded.tags,
                        url=upsert.excluded.url,
                        source_last_updated=upsert.excluded.source_last_updated,
                        source_display_id=upsert.excluded.source_display_id,
                        source_state=upsert.excluded.source_state,
                        parent_source_display_id=upsert.excluded.parent_source_display_id,
                        last_sync=upsert.excluded.last_sync,
                        api_payload=upsert.excluded.api_payload,
                        commit_identifiers=upsert.excluded.commit_identifiers
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
                    is_epic=work_item.is_epic,
                    parent_source_display_id=work_item.parent_source_display_id,
                    parent_key=work_item.parent_key,
                    tags=work_item.tags,
                    state=work_item.source_state,
                    created_at=work_item.source_created_at,
                    updated_at=work_item.source_last_updated,
                    last_sync=work_item.last_sync,
                    source_id=work_item.source_id,
                    commit_identifiers=work_item.commit_identifiers
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
                    is_epic=work_item.is_epic,
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
                        work_items.join(work_items_sources,
                                        work_items.c.work_items_source_id == work_items_sources.c.id)
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
                    and_(
                        work_items_sources.c.project_id != None,
                        work_items_sources.c.integration_type.in_([
                            WorkTrackingIntegrationType.github.value,
                            WorkTrackingIntegrationType.pivotal.value
                        ]),
                        work_items_sources.c.import_state == WorkItemsSourceImportState.auto_update.value
                    )
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
    elif WorkTrackingIntegrationType.gitlab.value == integration_type:
        return work_items_source_input['gitlab_parameters']
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


def sync_work_item(work_items_source_key, work_item_data, join_this=None):
    with db.orm_session(join_this) as session:
        work_item_key = None
        work_items_source = WorkItemsSource.find_by_key(session, work_items_source_key)
        parent_source_display_id = work_item_data.get('parent_source_display_id')
        if work_items_source:
            sync_result = dict()
            work_item = WorkItem.find_by_source_display_id(
                session,
                work_items_source.id,
                work_item_data.get('source_display_id')
            )
            if work_item is None:
                # Try finding by source_id
                work_item = WorkItem.find_by_work_item_source_id_source_id(
                    session,
                    work_items_source.id,
                    work_item_data.get('source_id')
                )
            # Find linked parent work item
            # FIXME: Epics can be from a different work item source. But here we are setting parent ids \
            #  only when parent is from same work item source.
            if parent_source_display_id is None or parent_source_display_id == '':
                work_item_data['parent_id'] = None
            else:
                parent_work_item = WorkItem.find_by_source_display_id(
                    session,
                    work_items_source.id,
                    source_display_id=parent_source_display_id

                )
                work_item_data['parent_id'] = parent_work_item.id if parent_work_item else None
            if not work_item:
                work_item_key = uuid.uuid4()
                work_item = WorkItem(
                    key=work_item_key,
                    last_sync=datetime.utcnow(),
                    **work_item_data
                )
                work_items_source.work_items.append(work_item)
                sync_result['is_new'] = True

            else:
                work_item_key = work_item.key
                # work_item_data should have work_items_source_id field too
                work_item_data['work_items_source_id'] = work_items_source.id
                sync_result['is_updated'] = work_item.update(work_item_data)

        # The reason we do this flush and refetch from the database below as follows:

        # source_created and source_last_updated fields in the work_item_data come in as
        # ISO 8601 format strings but get converted to date times on write to the db by SQLAlchemy. However
        # the object instances that are in the session still are stored as strings. This
        # is the value that is in work_item in the block above this.

        # Sending this in-memory reference directly back out as the output of this method
        # causes all sorts of issues as the consumers of this method expect datetimes
        # instead of strings.

        # Rather than force everyone calling the api to convert strings to datetimes or to add new
        # constructors to manage the string to date parsing, we choose to simply
        # load the item back from the database and let SQLAlchemy deal with the datetime
        # conversion consistently.
        #
        # Probably not the most optimal way of doing this, and there may be other problems
        # we have not anticipated with doing this, but
        # it seems like the one with smallest impact surface area assuming ISO 8601 format strings
        # are being input which seems likely in all the integration use cases we have.
        # Might need to revisit if this turns out to be false.
        # This really feels like something
        # SQLAlchemy should handle "correctly" but for now it does not seem to.

        session.flush()
        work_item = session.connection().execute(
            select([work_items]).where(
                work_items.c.key == work_item_key
            )
        ).fetchone()
        if work_item:
            if work_item.parent_id is not None:
                parent_key = WorkItem.find_by_key(session, key=work_item.key).parent.key
            else:
                parent_key = None
            return dict(
                **sync_result,
                **dict(
                    key=work_item.key,
                    work_item_type=work_item.work_item_type,
                    display_id=work_item.source_display_id,
                    url=work_item.url,
                    name=work_item.name,
                    description=work_item.description,
                    is_bug=work_item.is_bug,
                    is_epic=work_item.is_epic,
                    parent_source_display_id=work_item.parent_source_display_id,
                    parent_key=parent_key,
                    tags=work_item.tags,
                    state=work_item.source_state,
                    created_at=work_item.source_created_at,
                    updated_at=work_item.source_last_updated,
                    last_sync=work_item.last_sync,
                    source_id=work_item.source_id,
                    commit_identifiers=work_item.commit_identifiers,
                    is_moved=work_item.is_moved
                )
            )
        else:
            raise ProcessingException(
                f'Could not load work_item after sync: '
                f' work_item_source_key: {work_items_source_key}'
                f" source_display_id: {work_item_data.get('source_display_id')}"
            )


def insert_work_item(work_items_source_key, work_item_data, join_this=None):
    return sync_work_item(work_items_source_key, work_item_data)


def update_work_item(work_items_source_key, work_item_data, join_this=None):
    return sync_work_item(work_items_source_key, work_item_data, join_this)


def move_work_item(source_work_items_source_key, target_work_items_source_key, work_item_data, join_this=None):
    with db.orm_session(join_this) as session:
        source_work_items_source = WorkItemsSource.find_by_key(session, source_work_items_source_key)
        target_work_items_source = WorkItemsSource.find_by_key(session, target_work_items_source_key)
        if target_work_items_source.import_state == WorkItemsSourceImportState.auto_update.value:
            work_item = WorkItem.find_by_work_item_source_id_source_id(
                session,
                str(source_work_items_source.id),
                work_item_data.get('source_id')
            )
            move_result = dict()
            if work_item:
                work_item_data['work_items_source_id'] = target_work_items_source.id
                # Preserve the parent key if the parent_source_display_id is same
                if work_item.parent_id is not None:
                    parent_work_item = WorkItem.find_by_id(session, id=work_item.parent_id)
                    if parent_work_item and work_item_data.get(
                            'parent_source_display_id') == parent_work_item.source_display_id:
                        work_item_data['parent_id'] = parent_work_item.id
                        parent_key = parent_work_item.key
                    else:
                        parent_key = None
                else:
                    parent_key = None
                move_result['is_moved'] = work_item.update(work_item_data)
                session.flush()
                work_item = session.connection().execute(
                    select([work_items]).where(
                        work_items.c.key == work_item.key
                    )
                ).fetchone()
                return dict(
                    **move_result,
                    **dict(
                        key=work_item.key,
                        work_item_type=work_item.work_item_type,
                        display_id=work_item.source_display_id,
                        url=work_item.url,
                        name=work_item.name,
                        description=work_item.description,
                        is_bug=work_item.is_bug,
                        is_epic=work_item.is_epic,
                        parent_source_display_id=work_item.parent_source_display_id,
                        parent_key=parent_key,
                        tags=work_item.tags,
                        state=work_item.source_state,
                        created_at=work_item.source_created_at,
                        updated_at=work_item.source_last_updated,
                        last_sync=work_item.last_sync,
                        source_id=work_item.source_id,
                        commit_identifiers=work_item.commit_identifiers
                    )
                )


def delete_work_item(work_items_source_key, work_item_data, join_this=None):
    with db.orm_session(join_this) as session:
        session.expire_on_commit = False
        work_items_source = WorkItemsSource.find_by_key(session, work_items_source_key)
        if work_items_source:
            work_item = WorkItem.find_by_source_display_id(
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
                    is_epic=work_item.is_epic,
                    parent_key=work_item.parent.key if work_item.parent_id is not None else None,
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
                            import_state=WorkItemsSourceImportState.ready.value,
                            **WorkItemsSource.populate_required_values(work_item_source=work_items_source)
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
                        url=upsert.excluded.url
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
                    description=work_items_source.description,
                    commit_mapping_scope=work_items_source.commit_mapping_scope,
                    work_items_source_type=work_items_source.work_items_source_type
                )
                for work_items_source in work_items_sources_before_insert
            ]


def import_project(
        account_key,
        organization_key,
        work_items_source_import,
        project_name=None,
        existing_project_key=None,
        join_this=None
):
    with db.orm_session(join_this) as session:
        if project_name is None and existing_project_key is None:
            raise ProcessingException('At least one of project_name or existing_project_key must be provided')

        if project_name is not None:
            project = Project(
                key=uuid.uuid4(),
                account_key=account_key,
                organization_key=organization_key,
                name=project_name
            )

        if existing_project_key is not None:
            project = Project.find_by_key(session, existing_project_key)

        if project is None:
            raise ProcessingException('Could not initialize project for import')

        for source in work_items_source_import:
            work_items_source = WorkItemsSource.find_by_key(session, source['work_items_source_key'])
            if work_items_source:
                import_days_param = dict(initial_import_days=source['import_days'])
                if work_items_source.parameters is not None:
                    work_items_source.parameters = {
                        **work_items_source.parameters,
                        **import_days_param
                    }
                else:
                    work_items_source.parameters = import_days_param

                work_items_source.organization_key = organization_key
                if work_items_source.account_key is None:
                    work_items_source.account_key = account_key

                if work_items_source.commit_mapping_scope == 'organization':
                    work_items_source.commit_mapping_scope_key = organization_key

                project.work_items_sources.append(work_items_source)
            else:
                raise ProcessingException(
                    f"could not find work items source with key {source['work_items_source_key']}"
                )
        session.add(project)

        return project


def import_work_items_source_custom_fields(work_items_source, custom_fields, join_this=None):
    work_items_source.custom_fields = custom_fields[0]
    return work_items_source.key


def get_imported_work_items_sources_count(connector_key, join_this=None):
    with db.orm_session(join_this) as session:
        return session.connection().execute(
            select([
                func.count(work_items_sources.c.id)
            ]).where(
                and_(
                    work_items_sources.c.connector_key == connector_key,
                    work_items_sources.c.project_id != None
                )
            )
        ).scalar()


def sync_work_items_for_epic(work_items_source_key, epic, work_item_list, join_this=None):
    # sync work items first then update parent_id
    if len(work_item_list) > 0:
        with db.orm_session(join_this) as session:
            synced_work_items = sync_work_items(work_items_source_key, work_item_list, join_this=session)
            work_items_temp = db.create_temp_table(
                'work_items_temp_table', [
                    Column('key', UUID(as_uuid=True), unique=True),
                    Column('parent_id', Integer)
                ]
            )
            work_items_temp.create(session.connection(), checkfirst=True)
            epic_work_item = WorkItem.find_by_key(session, epic['key'])
            session.connection().execute(
                work_items_temp.insert().values(
                    [
                        dict(
                            key=work_item['key'],
                            parent_id=epic_work_item.id
                        )
                        for work_item in synced_work_items
                    ]
                )
            )

            work_items_removed_from_epic = session.connection().execute(
                select([
                    *work_items.columns
                ]
                ).select_from(
                    work_items
                ).where(
                    and_(
                        work_items.c.parent_id == epic_work_item.id,
                        work_items.c.key.notin_([wi['key'] for wi in synced_work_items])
                    )

                )
            ).fetchall()

            if len(work_items_removed_from_epic) > 0:
                session.connection().execute(
                    work_items_temp.insert().values([
                        dict(
                            key=work_item['key'],
                            parent_id=None
                        )
                        for work_item in work_items_removed_from_epic
                    ]
                    )
                )

            # update work items
            session.connection().execute(
                work_items.update().where(
                    work_items.c.key == work_items_temp.c.key
                ).values(
                    parent_id=work_items_temp.c.parent_id
                )
            )

            # Collecting all work items inserted/updated
            work_items_upserted = []
            for work_item in synced_work_items:
                work_item['parent_key'] = epic_work_item.key
            work_items_upserted.extend(synced_work_items)
            additional_work_items_updated = [
                dict(
                    is_new=False,
                    key=work_item.key,
                    work_item_type=work_item.work_item_type,
                    display_id=work_item.source_display_id,
                    url=work_item.url,
                    name=work_item.name,
                    description=work_item.description,
                    is_bug=work_item.is_bug,
                    is_epic=work_item.is_epic,
                    parent_key=None,
                    tags=work_item.tags,
                    state=work_item.source_state,
                    created_at=work_item.source_created_at,
                    updated_at=work_item.source_last_updated,
                    last_sync=work_item.last_sync,
                    source_id=work_item.source_id
                )
                for work_item in work_items_removed_from_epic
            ]
            work_items_upserted.extend(additional_work_items_updated)
            return work_items_upserted


def get_work_items_source_epics(work_items_source, join_this=None):
    with db.orm_session(join_this) as session:
        epic_work_items = session.connection().execute(
            select([
                work_items.c.key,
                work_items.c.source_display_id.label('display_id'),
                work_items.c.work_item_type,
                work_items.c.url,
                work_items.c.name,
                work_items.c.description,
                work_items.c.is_bug,
                work_items.c.is_epic,
                work_items.c.tags,
                work_items.c.source_state.label('state'),
                work_items.c.source_created_at.label('created_at'),
                work_items.c.source_last_updated.label('updated_at'),
                work_items.c.source_id,
                literal(None).label('parent_key')
            ]).select_from(
                work_items
            ).where(
                and_(
                    work_items.c.work_items_source_id == work_items_source.id,
                    work_items.c.is_epic == True
                    # work_items.c.source_state == 'Open' # TODO: To be added as optional argument
                )
            )
        ).fetchall()

        return epic_work_items


def get_registered_webhooks(work_items_source_key, join_this=None):
    try:
        with db.orm_session(join_this) as session:
            work_items_source = WorkItemsSource.find_by_key(session, work_items_source_key)
            if work_items_source:
                logger.info(f'Getting registered webhooks for Work items source {work_items_source.name}')
                source_data = dict(work_items_source.source_data)
                registered_webhooks = []
                if source_data.get('active_webhook'):
                    registered_webhooks.extend(source_data.get('inactive_webhooks', []))
                    registered_webhooks.append(source_data.get('active_webhook'))
                return dict(
                    success=True,
                    work_items_source_key=work_items_source_key,
                    registered_webhooks=registered_webhooks
                )
            else:
                raise ProcessingException(f'Could not find work items source with key {work_items_source_key}')
    except SQLAlchemyError as exc:
        return db.process_exception("Register Webhook", exc)
    except Exception as e:
        return db.failure_message('Register Webhook', e)


def register_webhooks(work_items_source_key, webhook_info, join_this=None):
    try:
        with db.orm_session(join_this) as session:
            # Replaces active webhook with the latest registered webhook.
            # Moves old active webhook to inactive webhooks
            # Deletes inactive webhook ids which are passed in webhook info and present in source_data
            work_items_source = WorkItemsSource.find_by_key(session, work_items_source_key)
            if work_items_source is not None:
                logger.info(f'Registering webhook for work_items_source {work_items_source.name}')
                source_data = dict(work_items_source.source_data)
                if webhook_info['active_webhook']:
                    if source_data.get('active_webhook'):
                        inactive_webhooks = source_data.get('inactive_webhooks', [])
                        inactive_webhooks.append(source_data.get('active_webhook'))
                        source_data['inactive_webhooks'] = inactive_webhooks
                    source_data['active_webhook'] = webhook_info['active_webhook']
                for wid in webhook_info['deleted_webhooks']:
                    if source_data.get('inactive_webhooks') and wid in source_data.get('inactive_webhooks'):
                        source_data['inactive_webhooks'].remove(wid)
                if source_data.get('webhooks'):
                    del source_data['webhooks']
                work_items_source.source_data = source_data
                return dict(
                    success=True,
                    work_items_source_key=work_items_source_key
                )
            else:
                raise ProcessingException(f"Could not find work items source with key {work_items_source_key}")
    except SQLAlchemyError as exc:
        return db.process_exception("Register Webhook", exc)
    except Exception as e:
        return db.failure_message('Register Webhook', e)
