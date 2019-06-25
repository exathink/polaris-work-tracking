# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar
__version__ = '0.0.1'

import graphene

from polaris.graphql.interfaces import NamedNode
from polaris.integrations.graphql import IntegrationsQueryMixin, IntegrationsMutationsMixin
from .work_item_connector import WorkTrackingConnector
from .mutations import CreateWorkItemsSource


class Query(
    IntegrationsQueryMixin,
    graphene.ObjectType
):

    node = NamedNode.Field()
    work_tracking_connector = WorkTrackingConnector.Field()

    def resolve_work_tracking_connector(self, info, **kwargs):
        return WorkTrackingConnector.resolve_field(info, **kwargs)


class Mutations(
    IntegrationsMutationsMixin,
    graphene.ObjectType
):
    create_work_items_source = CreateWorkItemsSource.Field()


schema = graphene.Schema(query=Query, mutation=Mutations)
