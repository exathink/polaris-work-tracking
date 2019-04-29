# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2017) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar


from polaris.utils.config import get_config_provider
from polaris.integrations.atlassian_connect import PolarisAtlassianConnect
from polaris.work_tracking import publish
config_provider = get_config_provider()


class JiraConnectorContext:
    base_url = config_provider.get('JIRA_CONNECTOR_BASE_URL')
    app_name = "Polaris Jira Connector"
    addon_name = "Polaris Jira Connector"
    addon_key = "polaris.jira"
    addon_description = "Jira Connector for the Polaris Platform"
    addon_scopes = ["READ", "WRITE"]
    addon_version = 1


def init_connector(app):
    ac = PolarisAtlassianConnect(app, connector_context=JiraConnectorContext)

    @ac.lifecycle("installed")
    def lifecycle_installed(client):
        pass

    @ac.lifecycle("uninstalled")
    def lifecycle_uninstalled(client):
        pass

    @ac.lifecycle("enabled")
    def lifecycle_enabled(client):
        pass

    @ac.lifecycle("disabled")
    def lifecycle_disabled(client):
        pass

    @ac.webhook('jira:issue_created')
    def handle_jira_issue_created(client, event):
        publish.atlassian_connect_work_item_event(
            atlassian_connector_key=client.atlassianConnectorKey,
            atlassian_event_type='issue_created',
            atlassian_event=event
        )

    @ac.webhook('jira:issue_updated')
    def handle_jira_issue_updated(client, event):
        publish.atlassian_connect_work_item_event(
            atlassian_connector_key=client.atlassianConnectorKey,
            atlassian_event_type='issue_updated',
            atlassian_event=event
        )

    @ac.webhook('jira:issue_deleted')
    def handle_jira_issue_deleted(client, event):
        publish.atlassian_connect_work_item_event(
            atlassian_connector_key=client.atlassianConnectorKey,
            atlassian_event_type='issue_deleted',
            atlassian_event=event
        )

    @ac.webhook('project_created')
    def handle_project_created(client, event):
        publish.atlassian_connect_work_item_event(
            atlassian_connector_key=client.atlassianConnectorKey,
            atlassian_event_type='project_created',
            atlassian_event=event
        )

    @ac.webhook('project_updated')
    def handle_project_updated(client, event):
        publish.atlassian_connect_work_item_event(
            atlassian_connector_key=client.atlassianConnectorKey,
            atlassian_event_type='project_updated',
            atlassian_event=event
        )

    @ac.webhook('project_deleted')
    def handle_project_deleted(client, event):
        publish.atlassian_connect_work_item_event(
            atlassian_connector_key=client.atlassianConnectorKey,
            atlassian_event_type='project_updated',
            atlassian_event=event
        )



