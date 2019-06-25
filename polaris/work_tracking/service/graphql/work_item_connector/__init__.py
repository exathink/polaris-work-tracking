# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import graphene
from polaris.graphql.interfaces import NamedNode
from polaris.integrations.graphql.interfaces import ConnectorInfo
from polaris.integrations.graphql.connector import Connector, ConnectorNode, Connectors
from .selectable import ConnectorWorkItemsSourceNodes
from ..work_items_source import WorkItemsSourcesConnectionMixin


class WorkTrackingConnector(
    WorkItemsSourcesConnectionMixin,
    Connector
):
    class Meta:
        interfaces = (NamedNode, ConnectorInfo, )
        named_node_resolver = ConnectorNode
        connection_node_resolvers = {
            'work_items_sources': ConnectorWorkItemsSourceNodes,
        }
        connection_class = lambda: Connectors
