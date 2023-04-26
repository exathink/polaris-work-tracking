# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging

import polaris.work_tracking.db.model
from polaris.common import db
from polaris.common.enums import WorkItemsSourceImportState, TrackingReceiptState
from polaris.utils.config import get_config_provider
from polaris.work_tracking import publish
from polaris.work_tracking import work_items_source_factory, connector_factory
from polaris.work_tracking.db import api
from polaris.work_tracking.db.model import WorkItemsSource, Project
from polaris.utils.exceptions import ProcessingException
from polaris.integrations.db.api import tracking_receipt_updates
from polaris.common import db
from polaris.work_tracking.messages import ResolveWorkItemsForEpic

logger = logging.getLogger('polaris.work_tracking.work_tracker')
config = get_config_provider()


def success(result):
    return dict(success=True, **result)


def update_work_items_source_before_work_item_sync(work_items_source_provider):
    work_items_source = work_items_source_provider.work_items_source
    with db.orm_session() as session:
        session.add(work_items_source)
        if work_items_source.import_state == WorkItemsSourceImportState.ready.value:
            # Initial Import
            work_items_source.import_state = WorkItemsSourceImportState.importing.value
        if getattr(work_items_source_provider, 'before_work_item_sync', None):
            work_items_source_data = work_items_source_provider.before_work_item_sync()
            work_items_source.update(work_items_source_data)


def sync_work_item(token_provider, work_items_source_key, source_id):
    try:
        work_items_source_provider = work_items_source_factory.get_provider_impl(token_provider, work_items_source_key)
        work_items_source = work_items_source_provider.work_items_source
        sync_result = None
        if work_items_source.import_state != WorkItemsSourceImportState.disabled.value:
            if getattr(work_items_source_provider, 'fetch_work_item', None):
                work_item_data = work_items_source_provider.fetch_work_item(source_id)
                if work_item_data is not None:
                    sync_result =  api.sync_work_item(work_items_source_key, work_item_data)

        else:
            logger.info(f'Attempted to call sync_work_item on a disabled work_item_source: {work_items_source.key}.'
                        f'Sync request will be ignored')
        return sync_result

    except Exception as exc:
        logger.error(f"Unexpected error raised on sync_work_item {source_id}")
        raise ProcessingException(f"Unexpected error raised on sync_work_item {source_id}")


def sync_work_items(token_provider, work_items_source_key):
    work_items_source_provider = work_items_source_factory.get_provider_impl(token_provider, work_items_source_key)
    work_items_source = work_items_source_provider.work_items_source
    if work_items_source.import_state != WorkItemsSourceImportState.disabled.value:
        update_work_items_source_before_work_item_sync(work_items_source_provider)
        for work_items in work_items_source_provider.fetch_work_items_to_sync():
            yield api.sync_work_items(work_items_source_key, work_items) or []

        with db.orm_session() as session:
            session.add(work_items_source)
            work_items_source.import_state = WorkItemsSourceImportState.auto_update.value
            work_items_source.set_synced()
    else:
        logger.info(f'Attempted to call sync_work_items on a disabled work_item_source: {work_items_source.key}.'
                    f'Sync request will be ignored')





def create_work_items_source(work_items_source_input, channel=None):
    work_items_source = api.create_work_items_source(work_items_source_input)
    publish.work_items_source_created(work_items_source, channel)
    return work_items_source


def sync_work_items_sources(connector_key, tracking_receipt_key=None):
    connector = connector_factory.get_connector(connector_key=connector_key)
    if connector:
        with tracking_receipt_updates(
                tracking_receipt_key,
                start_info=f"Started refreshing projects for {connector.name}",
                success_info=f"Finished refreshing projects for {connector.name}",
                error_info=f"Error refreshing projects for {connector.name}"
        ):
            for work_items_sources in connector.fetch_work_items_sources_to_sync():
                yield api.sync_work_items_sources(connector, work_items_sources)

"""
Find the work items in reprocessed_work_items that have changed from the original work items in work_items_batch
and return a list of the changed work items
"""
def changed_work_items(work_items_batch, reprocessed_work_items, attributes_to_check):
    changed_items = reprocessed_work_items
    if attributes_to_check is not None:
        changed_items = []
        for work_item, reprocessed_work_item in zip(work_items_batch, reprocessed_work_items):
            if any(getattr(work_item, attr, None) != reprocessed_work_item.get(attr, None) for attr in attributes_to_check):
                changed_items.append(reprocessed_work_item)

    return changed_items



def reprocess_work_items(work_items_source_key, attributes_to_check=None, batch_size=1000, join_this=None):
    starting = None
    while True:
        # We always want to use a new session for each batch of work items
        # so that a single transaction covers the fetch of the batch, the remapping of the
        # payload, the sync of the changed items and any downstream processing triggered by the yield statement
        # The downstream usually yields to a publish operation to the message bus, and this transaction
        # should fail if the message publication fails.
        with db.orm_session(join_this) as session:
            work_items_source_provider = work_items_source_factory.get_provider_impl(None, work_items_source_key, join_this=session)
            original_work_items, starting = WorkItemsSource.fetch_work_items_batch(work_items_source_key, batch_size, starting)
            if len(original_work_items) > 0:
                reprocessed_work_items = [
                    work_items_source_provider.map_issue_to_work_item_data(work_item.api_payload)
                    for work_item in original_work_items
                ]
                changed_items = changed_work_items(original_work_items, reprocessed_work_items, attributes_to_check)
                yield api.sync_work_items(work_items_source_key, changed_items, session) or []


        if starting is None:
            break

def register_work_items_source_webhooks(connector_key, work_items_source_key, join_this=None):
    with db.orm_session(join_this) as session:
        try:
            connector = connector_factory.get_connector(connector_key=connector_key, join_this=session)
            if connector and getattr(connector, 'register_project_webhooks', None):
                work_items_source = WorkItemsSource.find_by_key(session, work_items_source_key=work_items_source_key)
                if work_items_source:
                    get_hooks_result = api.get_registered_webhooks(work_items_source_key, join_this=session)
                    if get_hooks_result['success']:
                        webhook_info = connector.register_project_webhooks(work_items_source.source_id,
                                                                           get_hooks_result['registered_webhooks'])
                        if webhook_info['success']:
                            register_result = api.register_webhooks(work_items_source_key, webhook_info,
                                                                    join_this=session)
                            if register_result['success']:
                                return dict(
                                    success=True,
                                    work_items_source_key=work_items_source_key
                                )
                            else:
                                return db.failure_message(
                                    f"Could not register webhook due to: {register_result.get('exception')}")
                else:
                    return db.failure_message(f"Could not find work items source with key {work_items_source_key}")
            elif connector:
                # TODO: Remove this when github and bitbucket register webhook implementation is done.
                return dict(
                    success=True,
                    work_items_source_key=work_items_source_key
                )
            else:
                return db.failure_message(f"Could not find connector with key {connector_key}")
        except ProcessingException as e:
            return db.failure_message(f"Register webhooks failed due to: {e}")


def register_work_items_sources_webhooks(connector_key, work_items_source_keys, join_this=None):
    result = []
    for work_items_source_key in work_items_source_keys:
        registration_status = register_work_items_source_webhooks(connector_key, work_items_source_key,
                                                                  join_this=join_this)
        if registration_status['success']:
            result.append(registration_status)
        else:
            result.append(dict(
                work_items_source_key=work_items_source_key,
                success=False,
                message=registration_status.get('message'),
                exception=registration_status.get('exception')
            ))
    return result


def import_projects(import_projects_input):
    projects = []
    # We execute this in a separate transaction because we need the transaction to commit before
    # publishing

    with db.orm_session() as session:
        account_key = import_projects_input['account_key']
        organization_key = import_projects_input['organization_key']

        for project in import_projects_input['projects']:
            imported = api.import_project(
                account_key,
                organization_key,
                project['work_items_sources'],
                project.get('imported_project_name'),
                project.get('existing_project_key'),
                join_this=session
            )
            projects.append(
                imported
            )
            if imported:  # FIXME: Convert api result to include a success param
                for work_items_source in imported.work_items_sources:
                    connector_key = work_items_source.connector_key
                    register_webhooks_result = register_work_items_source_webhooks(connector_key, work_items_source.key,
                                                                                   join_this=session)
                    if not register_webhooks_result['success']:
                        logger.error(
                            f"Register webhooks failed while importing projects: {register_webhooks_result.get('exception')}"
                        )
    # DB transaction has committed we can publish messages.
    for imported in projects:
        publish.project_imported(organization_key, imported)

    return projects


def update_work_items_source_custom_fields(update_work_items_source_custom_fields_input, join_this=None):
    projects = []
    try:
        with db.orm_session(join_this) as session:
            for params in update_work_items_source_custom_fields_input.work_items_sources:
                work_items_source = WorkItemsSource.find_by_key(session, params.work_items_source_key)
                if work_items_source and work_items_source.import_state == WorkItemsSourceImportState.auto_update.value:
                    connector = connector_factory.get_connector(connector_key=work_items_source.connector_key,
                                                                join_this=session)
                    if hasattr(connector, 'fetch_custom_fields') and callable(connector.fetch_custom_fields):
                        work_items_source.custom_fields = connector.fetch_custom_fields()
                        projects.append(params.work_items_source_key)
                else:
                    return db.failure_message(
                        f"Work Item source with key: {params.work_items_source_key} not available for this import")
            return success(dict(projects=projects))
    except Exception as e:
        return db.failure_message(f"Import work item source custom fields failed", e)





def test_work_tracking_connector(connector_key, join_this=None):
    with db.orm_session(join_this) as session:
        work_tracking_connector = connector_factory.get_connector(
            connector_key=connector_key,
            join_this=session
        )
        return work_tracking_connector.test()
