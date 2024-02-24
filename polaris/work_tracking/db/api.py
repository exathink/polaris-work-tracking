# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and

# Author: Krishna Kumar

import logging
import uuid
from datetime import datetime
from polaris.utils.collections import dict_drop
from sqlalchemy import select, and_, or_, func, literal, Column, Integer, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import insert, UUID
from sqlalchemy.exc import SQLAlchemyError

from polaris.common import db
from polaris.common.enums import WorkTrackingIntegrationType, WorkItemsSourceImportState
from polaris.utils.collections import dict_select
from polaris.utils.exceptions import IllegalArgumentError, ProcessingException
from .model import WorkItemsSource, work_items, work_items_sources, WorkItem, Project
from polaris.integrations.db.model import Connector

logger = logging.getLogger('polaris.work_tracker.db.api')

"""
Sync work item data in the incoming list with the work items.
New items are added and existing items are updated. 

This operation returns a list of work items that were inserted and updated as result of the
sync operation.

Note that the list of work items returned may be larger than the list of work items
that were passed in. This is because the work items returned may include work items
whose parent or child wor items were also updated as a result of resolving new parent child 
relationships. 

@param work_items_source_key: The key of the work items source to sync with.
@param work_item_list: The list of work items to sync.
@:return: A list of work items that were inserted and updated as result of the sync operation.

"""


def sync_work_items(work_items_source_key, work_item_list, join_this=None):
    def insert_incoming_into_work_items_temp(session, work_item_list, work_items_source, work_items_temp):
        last_sync = datetime.utcnow()
        return session.connection().execute(
            insert(work_items_temp).values(
                [
                    dict(
                        key=uuid.uuid4(),
                        work_items_source_id=work_items_source.id,
                        last_sync=last_sync,
                        is_new=True,  # we will mark existing later
                        has_changes=True,  # we will mark unchanged later.
                        **work_item
                    )
                    for work_item in work_item_list
                ]
            )
        ).rowcount

    def mark_existing_work_items_in_temp_table(session, work_items_temp):
        # mark existing items in the set. We need this to properly
        # return newly inserted vs existing items back to the
        # caller.
        current_items = select([
            work_items_temp.c.source_id
        ]).select_from(
            work_items_temp.join(
                work_items,
                and_(
                    work_items_temp.c.work_items_source_id == work_items.c.work_items_source_id,
                    work_items_temp.c.source_id == work_items.c.source_id
                )
            )
        ).alias()
        return session.connection().execute(
            work_items_temp.update().values(
                is_new=False
            ).where(
                current_items.c.source_id == work_items_temp.c.source_id
            )
        ).rowcount

    def mark_unchanged_work_items_in_temp_table(session, work_items_temp):
        attributes_to_check = ['name', 'description', 'is_bug', 'work_item_type', 'is_epic', 'tags', 'url',
                               'source_state',
                               'source_display_id', 'api_payload', 'work_items_source_id', 'commit_identifiers',
                               'parent_source_display_id','priority','releases','story_points','sprints','flagged','changelog']
        # mark unchanged items in the set. We use this downstream to
        # signal that there is no need to propagate this update beyond this subsystem.
        unchanged_items = select([
            work_items_temp.c.source_id
        ]).select_from(
            work_items_temp.join(
                work_items,
                and_(
                    work_items_temp.c.work_items_source_id == work_items.c.work_items_source_id,
                    work_items_temp.c.source_id == work_items.c.source_id
                )
            )
        ).where(
            and_(*[
                or_(
                    work_items.columns[attribute] == work_items_temp.columns[attribute],
                    # we need this clause here because if both values are null,
                    # postgres will not allow you to compare them with an == operator.
                    # so we have to explictly check that both values are null.
                    and_(
                        work_items.columns[attribute] == None,
                        work_items_temp.columns[attribute] == None
                    )
                )
                for attribute in attributes_to_check
            ])
        ).alias()
        return session.connection().execute(
            work_items_temp.update().values(
                has_changes=False
            ).where(
                unchanged_items.c.source_id == work_items_temp.c.source_id
            )
        ).rowcount

    def upsert_temp_table_items_into_work_items(session, work_items_temp):
        # Now  upsert work items temp into work items so that the
        # new items are inserted and existing item attributes are updated.
        # we need to strip out the extra columns that are not in work_items
        work_item_columns = [column for column in work_items_temp.columns if
                             column.name not in ['is_new', 'has_changes']]
        upsert = insert(work_items).from_select(
            [column.name for column in work_item_columns],
            select(work_item_columns)
        )
        return session.connection().execute(
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
                    priority=upsert.excluded.priority,
                    releases=upsert.excluded.releases,
                    story_points=upsert.excluded.story_points,
                    sprints=upsert.excluded.sprints,
                    flagged=upsert.excluded.flagged,
                    parent_source_display_id=upsert.excluded.parent_source_display_id,
                    parent_id=upsert.excluded.parent_id,
                    last_sync=upsert.excluded.last_sync,
                    api_payload=upsert.excluded.api_payload,
                    commit_identifiers=upsert.excluded.commit_identifiers
                )
            )
        ).rowcount

    def resolve_children_in_temp_table_with_parents_in_work_items(session, work_items_source, work_items_temp):
        # Resolve the parent_ids of any item in work_items_temp
        # whose parents are in work_items
        existing_parents = select([
            work_items_temp.c.key,
            work_items.c.id.label('parent_id')
        ]).select_from(
            # we are loading all work items_sources from the parent organization
            # here because we want to be able to link work items in one work items source to parents
            # in another work items source.
            work_items_sources.join(
                work_items,
                and_(
                    work_items.c.work_items_source_id == work_items_sources.c.id,
                    work_items_sources.c.organization_key == work_items_source.organization_key
                )
            ).join(
                work_items_temp,
                work_items_temp.c.parent_source_display_id == work_items.c.source_display_id
            )

        ).cte()
        return session.connection().execute(
            work_items_temp.update().values(
                parent_id=existing_parents.c.parent_id
            ).where(
                work_items_temp.c.key == existing_parents.c.key
            )
        ).rowcount

    def resolve_children_in_work_items_with_parents_in_temp_table(session, work_items_source, work_items_temp):
        # now we need to update the parent_ids of any items in work_items
        # whose parents are in work_items_temp.
        # these capture the items that we not updated in the previous steps
        # but whose parents can now be resolved, because they have arrived in work_items_temp.
        parent_work_items = work_items.alias()
        children_with_newly_resolved_parents = select([
            work_items.c.key,
            parent_work_items.c.id.label('parent_id')
        ]).select_from(
            work_items.join(
                work_items_sources, work_items.c.work_items_source_id == work_items_sources.c.id
            ).join(
                work_items_temp,
                work_items.c.parent_source_display_id == work_items_temp.c.source_display_id
            ).join(
                parent_work_items,
                work_items_temp.c.key == parent_work_items.c.key
            )
        ).where(
            work_items_sources.c.organization_key == work_items_source.organization_key
        ).alias()

        # now update the parent id of these children in the work items table
        session.connection().execute(
            work_items.update().values(
                parent_id=children_with_newly_resolved_parents.c.parent_id
            ).where(
                work_items.c.key == children_with_newly_resolved_parents.c.key
            )
        )
        # we need to record these new items that will be updated
        # as a side effect of the sync of the work item list into the work_items_temp
        # table return
        # these updates as part of the final result sync operation.
        # We need to do this *before* we update the parent id, because we will not know
        # which ones they are once we update the parent id in the following step.
        work_items_temp_column_names = [column.name for column in work_items_temp.columns]
        work_items_temp_columns = [column for column in work_items.columns if
                                   column.name in work_items_temp_column_names]
        insert_children_with_newly_resolved_parents_into_work_items_temp = \
            insert(work_items_temp).from_select(
                [
                    *[column.name for column in work_items_temp_columns],
                    'is_new',
                    'has_changes'
                ],
                select([
                    *work_items_temp_columns,
                    literal(False).label('is_new'),
                    literal(True).label('has_changes')

                ]).select_from(
                    work_items.join(
                        children_with_newly_resolved_parents,
                        work_items.c.key == children_with_newly_resolved_parents.c.key
                    )
                )
            )
        return session.connection().execute(
            # we may end up creating duplicates here since this operation is done
            # on work items already loaded from the temp table to work items.
            # but we always want to choose the original item in temp table because it has the
            # correct value of  the is_new flag so we ignore duplicate insertions.
            insert_children_with_newly_resolved_parents_into_work_items_temp.on_conflict_do_nothing(
                index_elements=['source_id'],
            )
        ).rowcount

    # main body
    if len(work_item_list) > 0:
        with db.orm_session(join_this) as session:
            work_items_source = WorkItemsSource.find_by_key(session, work_items_source_key)
            logger.info(f"sync_work_items: {work_items_source.name} started")
            work_items_temp = db.temp_table_from(
                work_items,
                table_name='work_items_temp',
                exclude_columns=[work_items.c.id],
                extra_columns=[
                    Column('is_new', Boolean),
                    Column('has_changes', Boolean)
                ]
            )
            UniqueConstraint(work_items_temp.c.source_id)

            # step: 0
            work_items_temp.create(session.connection(), checkfirst=True)

            # step: 1 Stage the incoming items
            incoming = insert_incoming_into_work_items_temp(session, work_item_list, work_items_source, work_items_temp)
            logger.info(f"sync_work_items_source: {incoming} rows inserted into temp table")

            # step: 2 Mark new items
            existing_items = mark_existing_work_items_in_temp_table(session, work_items_temp)
            logger.info(
                f"sync_work_items: there {existing_items} existing items and {len(work_item_list) - existing_items} new items")

            # step: 3 Mark unchanged items
            unchanged = mark_unchanged_work_items_in_temp_table(session, work_items_temp)
            logger.info(
                f"sync_work_items: {unchanged} existing items have no changes")

            # step 3: parent resolution phase 1
            # this marks the parent_ids of children in the temp table with parent in work items
            # this is the case where the child arrives before the parent or with the parent
            incoming_parents_resolved = resolve_children_in_temp_table_with_parents_in_work_items(session,
                                                                                                  work_items_source,
                                                                                                  work_items_temp)
            logger.info(f"sync_work_items: parent resolution phase 1 - "
                        f"{incoming_parents_resolved} items in the incoming list had existing parents in  work items")

            # step: 4 upsert the temp table into work items
            upserts = upsert_temp_table_items_into_work_items(session, work_items_temp)
            logger.info(
                f"sync_work_items: {upserts} items upserted into work items")

            # step 5: parent resolution phase 2
            # this marks the parent_ids of the children in work_items with parent in the temp table
            # This is the case when the child arrives before the parent.

            # Note: that this potentially inserts existing items into temp table as the newly updated children
            # need to be returned as updated work items in the result of the sync.
            existing_work_items_resolved = resolve_children_in_work_items_with_parents_in_temp_table(session,
                                                                                                     work_items_source,
                                                                                                     work_items_temp)
            logger.info(f"sync_work_items: {existing_work_items_resolved} existing work items had parent id resolved"
                        f" from items in the incoming list. These will be added to the resolution lists and marked as updated for"
                        f" downstream processing ")


            # we load all the work_items in the organization as the search set for parents
            # since we need to consider cross project parents.
            parent_work_items = select([work_items.c.id, work_items.c.key]).select_from(
                work_items.join(
                    work_items_sources, work_items.c.work_items_source_id == work_items_sources.c.id
                )
            ).where(
                work_items_sources.c.organization_key == work_items_source.organization_key
            ).alias()

            # Return the current state of the work_items in the work_items_temp_table.
            # include the is_new flag from the temp table.
            # Since we can potentially insert new items into work_items_temp as a
            # side effect of resolving parents of existing items, this
            # means that the size of the result set from this operation can be
            # bigger than the input list of this operation.
            #
            # For example, a single
            # new epic arriving after all it's children have arrived could lead
            # to the epic and all its children being returned as the changed items from this
            # sync operation.
            #
            # This is the correct behavior
            sync_result = session.connection().execute(
                select([
                    work_items,
                    work_items_sources.c.key.label('work_items_source_key'),
                    parent_work_items.c.key.label('parent_key'),
                    work_items_temp.c.is_new,
                    work_items_temp.c.has_changes
                ]
                ).distinct().select_from(
                    work_items_temp.join(
                        work_items,
                        work_items_temp.c.source_id == work_items.c.source_id
                    ).join(
                        work_items_sources, work_items.c.work_items_source_id == work_items_sources.c.id
                    ).outerjoin(
                        parent_work_items,
                        work_items.c.parent_id == parent_work_items.c.id
                    )
                )
            ).fetchall()
            logger.info(
                f"sync_work_items result:{len(work_item_list)} incoming items, {len(sync_result)} outgoing items")
            logger.info(f"sync_work_items: {work_items_source.name} completed")

            return [
                dict(
                    is_new=work_item.is_new,
                    key=work_item.key,
                    work_items_source_key=str(work_item.work_items_source_key),
                    work_item_type=work_item.work_item_type,
                    display_id=work_item.source_display_id,
                    url=work_item.url,
                    name=work_item.name,
                    description=work_item.description,
                    is_bug=work_item.is_bug,
                    is_epic=work_item.is_epic,
                    parent_source_display_id=work_item.parent_source_display_id,
                    parent_key=str(work_item.parent_key) if work_item.parent_key is not None else None,
                    tags=work_item.tags,
                    state=work_item.source_state,
                    created_at=work_item.source_created_at,
                    updated_at=work_item.source_last_updated,
                    last_sync=work_item.last_sync,
                    source_id=work_item.source_id,
                    commit_identifiers=work_item.commit_identifiers,
                    is_updated=work_item.has_changes,
                    priority=work_item.priority,
                    releases=work_item.releases,
                    story_points=work_item.story_points,
                    sprints=work_item.sprints,
                    flagged=work_item.flagged,
                    changelog=work_item.changelog

                )
                for work_item in sync_result
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


"""
Sync operation for a single work item. This now delegates fully to the sync_work_items method and 
can be considered a convenience wrapper for that method. Note that this method returns a
list of work items since the sync of a single work items may return more than one work item
if that sync results in parent/child relationships for other work items being resolved in the process. 

@:param work_items_source_key: The key of the work items source to sync the work item for
@:param work_item_data: The data of the work item to sync
@:param join_this: The session to join the transaction to
@:return: A list of work items that were updated

"""


def sync_work_item(work_items_source_key, work_item_data, join_this=None):
    logger.info(f'Sync work item called for work items source {work_items_source_key}')
    return sync_work_items(work_items_source_key, [work_item_data], join_this) or []


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
                            WorkTrackingIntegrationType.jira.value
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


def move_work_item(source_work_items_source_key, target_work_items_source_key, work_item_data, join_this=None):
    with db.orm_session(join_this) as session:
        source_work_items_source = WorkItemsSource.find_by_key(session, source_work_items_source_key)
        if target_work_items_source_key:
            target_work_items_source = WorkItemsSource.find_by_key(session, target_work_items_source_key)
        work_item = WorkItem.find_by_work_item_source_id_source_id(
            session,
            str(source_work_items_source.id),
            work_item_data.get('source_id')
        )
        if work_item:
            # Find parent key of work item to pass in return value. Needed for composing message.
            if work_item.parent_id is not None:
                parent_work_item = WorkItem.find_by_id(session, id=work_item.parent_id)
                parent_key = parent_work_item.key
            else:
                parent_key = None
            if target_work_items_source_key is None or (target_work_items_source is None) or (
                    target_work_items_source and target_work_items_source.import_state != WorkItemsSourceImportState.auto_update.value):
                work_item.is_moved_from_current_source = True
                is_moved = True
            else:
                work_item_data['work_items_source_id'] = target_work_items_source.id
                # Set parent key to null if parent_source_display_id is not passed as same. Ideally it would be same or null.
                if parent_key:
                    if work_item_data.get('parent_source_display_id') == parent_work_item.source_display_id:
                        work_item_data['parent_id'] = parent_work_item.id
                    else:
                        parent_key = None
                work_item_data['is_moved_from_current_source'] = False
                is_moved = work_item.update(work_item_data)
                session.flush()
                work_item = session.connection().execute(
                    select([work_items]).where(
                        work_items.c.key == work_item.key
                    )
                ).fetchone()
            return dict(
                is_moved=is_moved,
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
                is_moved_from_current_source=work_item.is_moved_from_current_source,

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
                    is_deleted=True,
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
            else:
                raise ProcessingException(
                    f"Could not find work item with source id {work_item_data.get('source_display_id')}")
        else:
            raise ProcessingException(f"Could not find work items source with key f{work_items_source_key}")


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
                        url=upsert.excluded.url,
                        commit_mapping_prefix=upsert.excluded.commit_mapping_prefix
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


def update_work_items_source_parameters(connector_key, work_items_source_keys, work_items_source_parameters,
                                        join_this=None):
    try:
        with db.orm_session(join_this) as session:
            connector = Connector.find_by_key(session, connector_key)
            if connector is not None:
                updated = 0
                for work_items_source_key in work_items_source_keys:
                    work_items_source = WorkItemsSource.find_by_key(session, work_items_source_key)
                    if work_items_source is not None:
                        if str(work_items_source.connector_key) == connector_key:
                            work_items_source.update_parameters(work_items_source_parameters)
                            updated = updated + 1
                        else:
                            raise ProcessingException(
                                f'The work items source {work_items_source.name} with key {work_items_source_key}'
                                f'does not belong to the connector with key {connector_key}')

        return dict(
            success=True,
            updated=updated
        )

    except SQLAlchemyError as exc:
        return db.process_exception("update_work_items_source_parameters", exc)
    except Exception as e:
        return db.failure_message('update_work_items_source_parameters', e)
