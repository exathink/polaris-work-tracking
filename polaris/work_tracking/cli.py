# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging

import argh

import polaris.work_tracking.connector_factory
from polaris.common import db
from polaris.messaging.messages import ImportWorkItems
from polaris.messaging.topics import WorkItemsTopic
from polaris.messaging.utils import publish
from polaris.utils.exceptions import ProcessingException
from polaris.utils.logging import config_logging
from polaris.utils.token_provider import get_token_provider
from polaris.work_tracking import commands

logger = logging.getLogger('polaris.work_tracking.cli')
token_provider = get_token_provider()

db.init()


def import_work_items(organization_key=None, work_items_source_key=None):
    publish(WorkItemsTopic,
            ImportWorkItems(send=dict(organization_key=organization_key, work_items_source_key=work_items_source_key)))


def import_work_items_sources(connector_name):
    connector = polaris.work_tracking.connector_factory.get_connector(connector_name="Polaris Gitlab")
    if connector:
        for work_items_sources in commands.sync_work_items_sources(connector.key):
            print(work_items_sources)
    else:
        raise ProcessingException(f'Could not find connector with name {connector_name}')


def list_jira_projects(connector_name):
    connector = polaris.work_tracking.connector_factory.get_connector(connector_name=connector_name)

    for work_items_sources in connector.fetch_work_items_sources_to_sync(batch_size=50):
        for source in work_items_sources:
            print(source)


if __name__ == '__main__':
    config_logging(
        suppress=['requests.packages.urllib3.connectionpool']
    )

    argh.dispatch_commands([
        import_work_items_sources,
        import_work_items,
        list_jira_projects
    ])
