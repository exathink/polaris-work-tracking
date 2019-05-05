# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2017) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging
from polaris.utils.config import get_config_provider
from polaris.integrations.atlassian_connect import PolarisAtlassianConnect
from polaris.work_tracking import publish

log = logging.getLogger('polaris.work_tracking.jira_connector')

config_provider = get_config_provider()


class JiraConnectorContext:
    base_url = config_provider.get('JIRA_CONNECTOR_BASE_URL')
    mount_path = config_provider.get('JIRA_CONNECTOR_MOUNT_PATH')

    app_name = "Polaris Jira Connector"
    addon_name = "Polaris Jira Connector"
    addon_key = config_provider.get('JIRA_CONNECTOR_APP_KEY', 'polaris.jira')
    addon_description = "Jira Connector for the Polaris Platform"
    addon_scopes = ["READ", "WRITE"]
    addon_version = 1


def init_connector(app):

    log.info("Initializing Atlassian Connector")

    ac = PolarisAtlassianConnect(app, connector_context=JiraConnectorContext)

    @ac.lifecycle("installed")
    def lifecycle_installed(client):
        log.info(f'Connector installed: {client.baseUrl} ({client.clientKey})')

    @ac.lifecycle("uninstalled")
    def lifecycle_uninstalled(client):
        log.info(f'Connector uninstalled: {client.baseUrl} ({client.clientKey})')

    @ac.lifecycle("enabled")
    def lifecycle_enabled(client):
        log.info(f'Connector enabled: {client.baseUrl} ({client.clientKey})')

    @ac.lifecycle("disabled")
    def lifecycle_disabled(client):
        log.info(f'Connector disabled: {client.baseUrl} ({client.clientKey})')

    @ac.webhook('jira:issue_created')
    def handle_jira_issue_created(client, event):
        log.info(f'Issue Created: {client.baseUrl} ({client.clientKey})')
        publish.atlassian_connect_work_item_event(
            atlassian_connector_key=client.atlassianConnectorKey,
            atlassian_event_type='issue_created',
            atlassian_event=event
        )

    @ac.webhook('jira:issue_updated')
    def handle_jira_issue_updated(client, event):
        log.info(f'Issue Updated: {client.baseUrl} ({client.clientKey})')
        publish.atlassian_connect_work_item_event(
            atlassian_connector_key=client.atlassianConnectorKey,
            atlassian_event_type='issue_updated',
            atlassian_event=event
        )

    @ac.webhook('jira:issue_deleted')
    def handle_jira_issue_deleted(client, event):
        log.info(f'Issue Deleted: {client.baseUrl} ({client.clientKey})')
        publish.atlassian_connect_work_item_event(
            atlassian_connector_key=client.atlassianConnectorKey,
            atlassian_event_type='issue_deleted',
            atlassian_event=event
        )

    @ac.webhook('project_created')
    def handle_project_created(client, event):
        log.info(f'Project Created: {client.baseUrl} ({client.clientKey})')
        publish.atlassian_connect_work_item_event(
            atlassian_connector_key=client.atlassianConnectorKey,
            atlassian_event_type='project_created',
            atlassian_event=event
        )

    @ac.webhook('project_updated')
    def handle_project_updated(client, event):
        log.info(f'Project Updated: {client.baseUrl} ({client.clientKey})')
        publish.atlassian_connect_work_item_event(
            atlassian_connector_key=client.atlassianConnectorKey,
            atlassian_event_type='project_updated',
            atlassian_event=event
        )

    @ac.webhook('project_deleted')
    def handle_project_deleted(client, event):
        log.info(f'Project Deleted: {client.baseUrl} ({client.clientKey})')
        publish.atlassian_connect_work_item_event(
            atlassian_connector_key=client.atlassianConnectorKey,
            atlassian_event_type='project_updated',
            atlassian_event=event
        )




