# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging

import graphene

from polaris.common import db
from polaris.common.enums import WorkTrackingIntegrationType
from polaris.integrations import publish as integrations_publish
from polaris.integrations.db.api import create_connector, create_tracking_receipt, \
    delete_connector, archive_connector, update_connector
from polaris.integrations.graphql.connector.mutations import DeleteConnector, CreateConnector, EditConnector
from polaris.utils.exceptions import ProcessingException
from polaris.work_tracking import commands
from polaris.work_tracking import publish
from polaris.work_tracking.db import api
from polaris.work_tracking.integrations import pivotal_tracker, github
from polaris.work_tracking.integrations.atlassian import jira_work_items_source
from .work_tracking_connector import WorkTrackingConnector

logger = logging.getLogger('polaris.work_tracking.mutations')

# Input Types
IntegrationType = graphene.Enum.from_enum(WorkTrackingIntegrationType)
GithubSourceType = graphene.Enum.from_enum(github.GithubWorkItemSourceType)
PivotalSourceType = graphene.Enum.from_enum(pivotal_tracker.PivotalWorkItemSourceType)
JiraSourceType = graphene.Enum.from_enum(jira_work_items_source.JiraWorkItemSourceType)


class CommitMappingScope(graphene.Enum):
    organization = 'organization'
    project = 'project'
    repository = 'repository'


class GithubWorkItemSourceParams(graphene.InputObjectType):
    work_items_source_type = GithubSourceType(required=True)

    organization = graphene.String(required=True)
    repository = graphene.String(required=False)
    bug_tags = graphene.List(graphene.String)


class PivotalWorkItemsSourceParams(graphene.InputObjectType):
    work_items_source_type = PivotalSourceType(required=True)

    name = graphene.String(required=True)
    id = graphene.String(required=True)


class JiraWorkItemsSourceParams(graphene.InputObjectType):
    work_items_source_type = JiraSourceType(required=True)
    jira_connector_key = graphene.String(required=True)
    project_id = graphene.String(required=True)
    initial_import_days = graphene.Int(required=False)


class WorkItemsSourceInput(graphene.InputObjectType):
    key = graphene.String(required=False)
    integration_type = IntegrationType(required=True)
    name = graphene.String(required=True)
    pivotal_parameters = PivotalWorkItemsSourceParams(required=False)
    github_parameters = GithubWorkItemSourceParams(required=False)
    jira_parameters = JiraWorkItemsSourceParams(required=False)

    description = graphene.String(required=False)
    account_key = graphene.String(required=True)
    organization_key = graphene.String(required=True)
    commit_mapping_scope = CommitMappingScope(required=True)
    commit_mapping_scope_key = graphene.String(required=True)


# Mutations

class CreateWorkItemsSource(graphene.Mutation):
    class Arguments:
        data = WorkItemsSourceInput(required=True)

    name = graphene.String()
    key = graphene.String()

    def mutate(self, info, data):
        logger.info('CreateWorkItemsSource called')
        work_items_source = commands.create_work_items_source(work_items_source_input=data)
        return CreateWorkItemsSource(
            name=work_items_source.name,
            key=work_items_source.key
        )


class WorkItemsSourceImport(graphene.InputObjectType):
    work_items_source_name = graphene.String(required=True)
    work_items_source_key = graphene.String(required=True)
    import_days = graphene.Int(required=True)


class ProjectImport(graphene.InputObjectType):
    # At least of imported_project_name or existing_project_key must be provided.
    imported_project_name = graphene.String(required=False)
    existing_project_key = graphene.String(required=False)

    work_items_sources = graphene.List(WorkItemsSourceImport)


class ImportProjectsInput(graphene.InputObjectType):
    account_key = graphene.String(required=True)
    organization_key = graphene.String(required=True)
    projects = graphene.List(ProjectImport, required=True)


class ImportProjects(graphene.Mutation):
    class Arguments:
        import_projects_input = ImportProjectsInput(required=True)

    project_keys = graphene.List(graphene.String)

    def mutate(self, info, import_projects_input):
        projects = commands.import_projects(import_projects_input)
        return ImportProjects(
            project_keys=[project.key for project in projects]
        )


class RefreshConnectorProjectsInput(graphene.InputObjectType):
    connector_key = graphene.String(required=True)
    track = graphene.Boolean(required=False, default_value=False)


class RefreshConnectorProjects(graphene.Mutation):
    class Arguments:
        refresh_connector_projects_input = RefreshConnectorProjectsInput(required=True)

    success = graphene.Boolean()
    tracking_receipt_key = graphene.String(required=False)

    def mutate(self, info, refresh_connector_projects_input):
        with db.orm_session() as session:
            tracking_receipt = None
            if refresh_connector_projects_input.track:
                tracking_receipt = create_tracking_receipt(
                    name='RefreshConnectorProjectsMutation',
                    join_this=session
                )

            publish.refresh_connector_projects(refresh_connector_projects_input['connector_key'], tracking_receipt)

            return RefreshConnectorProjects(
                success=True,
                tracking_receipt_key=tracking_receipt.key if tracking_receipt else None
            )


class TestConnectorInput(graphene.InputObjectType):
    connector_key = graphene.String(required=True)


class TestWorkTrackingConnector(graphene.Mutation):
    class Arguments:
        test_connector_input = TestConnectorInput(required=True)

    success = graphene.Boolean()

    def mutate(self, info, test_connector_input):
        connector_key = test_connector_input.connector_key
        logger.info(f'Test Connector called for connector {connector_key}')
        with db.orm_session() as session:
            return TestWorkTrackingConnector(
                success=commands.test_work_tracking_connector(connector_key, join_this=session)
            )


class CreateWorkTrackingConnector(CreateConnector):
    connector = WorkTrackingConnector.Field(key_is_required=False)

    def mutate(self, info, create_connector_input):
        logger.info('Create WorkTracking Connector called')
        with db.orm_session() as session:
            connector = create_connector(create_connector_input.connector_type, create_connector_input,
                                         join_this=session)

            # if the connector is created in a non-enabled state (Atlassian for example)
            # we cannot test it. So default is assume test pass.
            can_create = True
            if connector.state == 'enabled':
                can_create = commands.test_work_tracking_connector(connector.key, join_this=session)

            if can_create:
                resolved = CreateConnector(
                    connector=WorkTrackingConnector.resolve_field(info, connector.key)
                )
                # Do the publish right at the end.
                integrations_publish.connector_created(connector)
                return resolved
            else:
                raise ProcessingException("Could not create connector: Connector test failed")


class EditWorkTrackingConnector(EditConnector):
    connector = WorkTrackingConnector.Field(key_is_required=False)

    def mutate(self, info, edit_connector_input):
        logger.info('Create WorkTracking Connector called')
        with db.orm_session() as session:
            connector = update_connector(edit_connector_input.connector_type, edit_connector_input,
                                         join_this=session)
            if commands.test_work_tracking_connector(connector.key, join_this=session):
                resolved = EditConnector(
                    connector=WorkTrackingConnector.resolve_field(info, connector.key)
                )
                # Do the publish right at the end.
                # integrations_publish.connector_created(connector)
                return resolved
            else:
                raise ProcessingException("Could not create connector: Connector test failed")


class DeleteWorkTrackingConnector(DeleteConnector):
    def mutate(self, info, delete_connector_input):
        connector_key = delete_connector_input['connector_key']
        with db.orm_session() as session:
            if api.get_imported_work_items_sources_count(connector_key, session) > 0:
                return DeleteWorkTrackingConnector(
                    connector_name=archive_connector(connector_key, session),
                    disposition='archived'
                )
            else:
                return DeleteWorkTrackingConnector(
                    connector_name=delete_connector(connector_key, session),
                    disposition='deleted'
                )


