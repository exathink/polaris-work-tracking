# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging

from polaris.common import db
from polaris.common.enums import WorkItemsSourceImportState, TrackingReceiptState
from polaris.utils.config import get_config_provider
from polaris.work_tracking import publish
from polaris.work_tracking import work_items_source_factory, connector_factory
from polaris.work_tracking.db import api
from polaris.integrations.db.api import tracking_receipt_updates

logger = logging.getLogger('polaris.work_tracking.work_tracker')
config = get_config_provider()


def sync_work_items(token_provider, work_items_source_key):
    work_items_source_provider = work_items_source_factory.get_provider_impl(token_provider, work_items_source_key)
    work_items_source = work_items_source_provider.work_items_source
    if work_items_source.import_state != WorkItemsSourceImportState.disabled.value:
        if work_items_source.import_state == WorkItemsSourceImportState.ready.value:
            # Initial Import
            with db.orm_session() as session:
                session.add(work_items_source)
                work_items_source.import_state = WorkItemsSourceImportState.importing.value

        for work_items in work_items_source_provider.fetch_work_items_to_sync():
            yield api.sync_work_items(work_items_source_key, work_items) or []

        with db.orm_session() as session:
            session.add(work_items_source)
            work_items_source.import_state = WorkItemsSourceImportState.auto_update.value
            work_items_source.set_synced()
    else:
        logger.info(f'Attempted to call sync_work_items on a disabled work_item_source: {work_items_source.key}.'
                    f'Sync request will be ignored')


def sync_work_items_for_epic(work_items_source_key, epic):
    work_items_source_provider = work_items_source_factory.get_provider_impl(None, work_items_source_key)
    work_items_source = work_items_source_provider.work_items_source
    if work_items_source and work_items_source.import_state == WorkItemsSourceImportState.auto_update.value:
        for work_items in work_items_source_provider.fetch_work_items_for_epic(epic):
            yield api.sync_work_items_for_epic(work_items_source_key, epic, work_items) or []
    else:
        logger.info(
            f'Attempted to call sync_work_items_with_epic_id on a disabled work_item_source: {work_items_source.key}.'
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
    # DB transaction has commited we can publish messages.
    for imported in projects:
        publish.project_imported(organization_key, imported)

    return projects


def test_work_tracking_connector(connector_key, join_this=None):
    with db.orm_session(join_this) as session:
        work_tracking_connector = connector_factory.get_connector(
            connector_key=connector_key,
            join_this=session
        )
        return work_tracking_connector.test()
