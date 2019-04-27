# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2017) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar


from flask import jsonify
from polaris.utils.config import get_config_provider
from polaris.integrations.atlassian_connect import PolarisAtlassianConnect, _PolarisAtlassianConnectLoader

config_provider = get_config_provider()


class JiraConnectorContext:
    base_url = config_provider.get('JIRA_CONNECTOR_BASE_URL')
    app_name = "Polaris Jira Connector"
    addon_name = "Polaris Jira Connector"
    addon_key = "polaris.jira"
    addon_description = "Jira Connector for the Polaris Platform"
    addon_scopes = ["READ", "WRITE"]


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
        pass



