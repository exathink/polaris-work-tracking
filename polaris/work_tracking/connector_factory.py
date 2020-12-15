# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar
from polaris.common import db
from polaris.common.enums import ConnectorType, ConnectorProductType
from polaris.integrations.db.api import find_connector, find_connector_by_name
from polaris.utils.exceptions import ProcessingException
from polaris.work_tracking.integrations.atlassian.jira_connector import JiraConnector
from polaris.work_tracking.integrations.pivotal_tracker import PivotalTrackerConnector
from polaris.work_tracking.integrations.github import GithubWorkTrackingConnector
from polaris.work_tracking.integrations.gitlab import GitlabWorkTrackingConnector


def get_connector(connector_name=None, connector_key=None, join_this=None):
    with db.orm_session(join_this) as session:

        if connector_key is not None:
            connector = find_connector(connector_key, join_this=session)
        if connector_name is not None:
            connector = find_connector_by_name(connector_name, join_this=session)
        if connector:
            if connector.type == ConnectorType.atlassian.value and connector.product_type == ConnectorProductType.jira.value:
                return JiraConnector(connector)
            elif connector.type == ConnectorType.pivotal.value:
                return PivotalTrackerConnector(connector)
            elif connector.type == ConnectorType.github.value:
                return GithubWorkTrackingConnector(connector)
            elif connector.type == ConnectorType.gitlab.value:
                return GitlabWorkTrackingConnector(connector)
            else:
                raise ProcessingException(f'Cannot create a work tracking connector for connector_key {connector_key}')

        else:
            raise ProcessingException(f'Connot find connector for connector_key {connector_key}')
