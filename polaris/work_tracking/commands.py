# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging

from polaris.common import db
from polaris.utils.config import get_config_provider
from polaris.utils.exceptions import ProcessingException
from polaris.work_tracking import publish
from polaris.work_tracking import work_items_source_factory
from polaris.work_tracking.db import api
from polaris.work_tracking.db.model import WorkItemsSource

logger = logging.getLogger('polaris.work_tracking.work_tracker')
config = get_config_provider()


def sync_work_items(token_provider, work_items_source_key):
    with db.orm_session() as session:
        session.expire_on_commit = False
        work_items_source = WorkItemsSource.find_by_work_items_source_key(session, work_items_source_key)
        if work_items_source is not None:
            work_items_source_impl = work_items_source_factory.get_work_items_source_impl(token_provider, work_items_source)
        else:
            raise ProcessingException(f"Could not find work items source with key {work_items_source.key}")

    for work_items in work_items_source_impl.fetch_work_items_to_sync():
        yield api.sync_work_items(work_items_source_key, work_items) or []

    with db.orm_session() as session:
        work_items_source.set_synced()
        session.add(work_items_source)




def create_work_items_source(work_items_source_input, channel=None):
    work_items_source = api.create_work_items_source(work_items_source_input)
    publish.work_items_source_created(work_items_source, channel)
    return work_items_source



def sync_work_items_sources(connector_key):
    connector = work_items_source_factory.get_connector_impl(connector_key)
    if connector:
        for work_items_sources in connector.fetch_work_items_sources_to_sync():
            yield api.sync_work_items_sources(connector_key, work_items_sources)



