# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from polaris.integrations.db import api


def list_projects(jira_connector_key):
    jira_connector = api.find_atlassian_connect_record_by_key(jira_connector_key)
    url = jira_connector.api_url('/project/search')
    response = jira_connector.get(url)
    if response.ok:
        return response.json()
    else:
        return response.text

