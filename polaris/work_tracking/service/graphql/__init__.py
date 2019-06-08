# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar
__version__ = '0.0.1'

import graphene

from polaris.graphql.interfaces import NamedNode
from polaris.integrations.graphql import IntegrationsQueryMixin
from .mutations import CreateWorkItemsSource


class Query(
    IntegrationsQueryMixin,
    graphene.ObjectType
):

    node = NamedNode.Field()


class Mutations(graphene.ObjectType):
    create_work_items_source = CreateWorkItemsSource.Field()


schema = graphene.Schema(query=Query, mutation=Mutations)
