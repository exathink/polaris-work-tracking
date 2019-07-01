# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2019) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import graphene

from polaris.graphql.interfaces import NamedNode
from polaris.graphql.selectable import Selectable, CountableConnection, ConnectionResolverMixin
from .selectable import WorkItemsSourceNode, WorkItemsSourceWorkItemCount

from ..interface_mixins import WorkItemsSourceInfoResolverMixin, WorkItemCountResolverMixin
from ..interfaces import WorkItemsSourceInfo, WorkItemCount


class WorkItemsSource(
    WorkItemsSourceInfoResolverMixin,
    WorkItemCountResolverMixin,
    Selectable
):
    class Meta:
        interfaces = (NamedNode, WorkItemsSourceInfo, WorkItemCount)
        interface_resolvers = {
            'WorkItemCount': WorkItemsSourceWorkItemCount
        }
        named_node_resolver = WorkItemsSourceNode
        connection_class = lambda: WorkItemsSources

    @classmethod
    def ConnectionField(cls, named_node_resolver=None, **kwargs):
        return super().ConnectionField(
            named_node_resolver,
            unattachedOnly=graphene.Argument(
                graphene.Boolean, required=False,
                description='Only fetch work_items_sources that have project_id == null'
            ),
            projectKeys=graphene.Argument(
                graphene.List(graphene.String), required=False,
                description='Only fetch work items sources for the specified projects'
            ),
            **kwargs
        )

    @classmethod
    def resolve_field(cls, info, key, **kwargs):
        return cls.resolve_instance(key, **kwargs)


class WorkItemsSources(
    CountableConnection
):
    class Meta:
        node = WorkItemsSource


class WorkItemsSourcesConnectionMixin(ConnectionResolverMixin):

    work_items_sources = WorkItemsSource.ConnectionField()

    def resolve_work_items_sources(self, info, **kwargs):
        return WorkItemsSource.resolve_connection(
            self.get_connection_resolver_context('work_items_sources'),
            self.get_connection_node_resolver('work_items_sources'),
            self.get_instance_query_params(),
            **kwargs
        )


