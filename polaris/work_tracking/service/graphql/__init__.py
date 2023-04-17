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
from .work_tracking_connector import WorkTrackingConnector
from .work_items_source import WorkItemsSource
from .mutations import \
    CreateWorkItemsSource, ImportProjects, \
    RefreshConnectorProjects, DeleteWorkTrackingConnector, \
    CreateWorkTrackingConnector, TestWorkTrackingConnector, EditWorkTrackingConnector, \
    UpdateWorkItemsSourceCustomFields, ResolveWorkItemsForProjectEpics, \
    RegisterWorkItemsSourcesConnectorWebhooks, \
    SyncWorkItemsSource, \
    ImportWorkItems, \
    UpdateWorkItemsSourceSyncParameters


class Query(
    IntegrationsQueryMixin,
    graphene.ObjectType
):
    node = NamedNode.Field()
    work_tracking_connector = WorkTrackingConnector.Field()
    work_items_source = WorkItemsSource.Field()

    def resolve_work_tracking_connector(self, info, **kwargs):
        return WorkTrackingConnector.resolve_field(info, **kwargs)

    def resolve_work_items_source(self, info, **kwargs):
        return WorkItemsSource.resolve_field(info, **kwargs)


class Mutations(
    IntegrationsMutationsMixin,
    graphene.ObjectType
):
    create_work_items_source = CreateWorkItemsSource.Field()
    sync_work_items_source = SyncWorkItemsSource.Field()

    import_projects = ImportProjects.Field()
    import_work_items = ImportWorkItems.Field()

    update_work_items_source_custom_fields = UpdateWorkItemsSourceCustomFields.Field()
    update_work_items_source_sync_parameters = UpdateWorkItemsSourceSyncParameters.Field()

    resolve_work_items_for_project_epics = ResolveWorkItemsForProjectEpics.Field()
    register_work_items_source_connector_webhooks = RegisterWorkItemsSourcesConnectorWebhooks.Field()
    refresh_connector_projects = RefreshConnectorProjects.Field()
    test_connector = TestWorkTrackingConnector.Field()

    # oveerides from integrations connector
    delete_connector = DeleteWorkTrackingConnector.Field()
    create_connector = CreateWorkTrackingConnector.Field()
    edit_connector = EditWorkTrackingConnector.Field()


schema = graphene.Schema(query=Query, mutation=Mutations)
