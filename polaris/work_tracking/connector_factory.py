# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar
from polaris.common import db
from polaris.common.enums import ConnectorType
from polaris.integrations.db.api import find_connector
from polaris.utils.exceptions import ProcessingException
from polaris.work_tracking.integrations.atlassian.jira_connector import JiraConnector


def get_connector(connector_key):
    with db.orm_session() as session:
        connector = find_connector(connector_key, join_this=session)
        if connector:
            if connector.type == ConnectorType.atlassian.value and connector.product_type == 'jira':
                return JiraConnector(connector)

            else:
                raise ProcessingException(f'Cannot create a work tracking connector for connector_key {connector_key}')

        else:
            raise ProcessingException(f'Connot find connector for connector_key {connector_key}')