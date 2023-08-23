# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging

import graphene
import jmespath

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
from polaris.work_tracking.integrations import pivotal_tracker, github, gitlab
from polaris.work_tracking.integrations.atlassian import jira_work_items_source
from .work_tracking_connector import WorkTrackingConnector
from polaris.work_tracking.enums import CustomTagMappingType

logger = logging.getLogger('polaris.work_tracking.mutations')

# Input Types
IntegrationType = graphene.Enum.from_enum(WorkTrackingIntegrationType)
GithubSourceType = graphene.Enum.from_enum(github.GithubWorkItemSourceType)
GitlabSourceType = graphene.Enum.from_enum(gitlab.GitlabWorkItemSourceType)
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


class GitlabWorkItemSourceParams(graphene.InputObjectType):
    work_items_source_type = GitlabSourceType(required=True)

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
    gitlab_parameters = GitlabWorkItemSourceParams(required=False)

    description = graphene.String(required=False)
    account_key = graphene.String(required=True)
    organization_key = graphene.String(required=True)
    commit_mapping_scope = CommitMappingScope(required=True)
    commit_mapping_scope_key = graphene.String(required=True)


# Mutations

class CreateWorkItemsSource(graphene.Mutation):
    class Arguments:
        create_work_items_source_input = WorkItemsSourceInput(required=True)

    name = graphene.String()
    key = graphene.String()

    def mutate(self, info, create_work_items_source_input):
        logger.info('CreateWorkItemsSource called')
        work_items_source = commands.create_work_items_source(work_items_source_input=create_work_items_source_input)
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


class ReprocessWorkItemsInput(graphene.InputObjectType):
    organization_key = graphene.String(required=True)
    work_items_source_key = graphene.String(required=True)
    attributes_to_check = graphene.List(graphene.String,required=False)

class ImportProjects(graphene.Mutation):
    class Arguments:
        import_projects_input = ImportProjectsInput(required=True)

    project_keys = graphene.List(graphene.String)

    def mutate(self, info, import_projects_input):
        projects = commands.import_projects(import_projects_input)
        return ImportProjects(
            project_keys=[project.key for project in projects]
        )


class WorkItemSourceParams(graphene.InputObjectType):
    work_items_source_key = graphene.String(required=True)


class UpdateWorkItemsSourceCustomFieldsInput(graphene.InputObjectType):
    work_items_sources = graphene.List(WorkItemSourceParams)


class UpdateWorkItemsSourceCustomFields(graphene.Mutation):
    class Arguments:
        update_work_items_source_custom_fields_input = UpdateWorkItemsSourceCustomFieldsInput(required=True)

    success = graphene.Boolean()
    error_message = graphene.String()

    def mutate(self, info, update_work_items_source_custom_fields_input):
        logger.info("UpdateWorkItemsSourceCustomFields called")
        with db.orm_session() as session:
            result = commands.update_work_items_source_custom_fields(update_work_items_source_custom_fields_input,
                                                                     join_this=session)
            return UpdateWorkItemsSourceCustomFields(success=result['success'], error_message=result.get('message'))


class SyncWorkItemsSourceInput(graphene.InputObjectType):
    organization_key = graphene.String(required=True)
    work_items_source_key = graphene.String(required=True)


class SyncWorkItemsSource(graphene.Mutation):
    class Arguments:
        sync_work_items_source_input = SyncWorkItemsSourceInput(required=True)

    success = graphene.Boolean()

    def mutate(self, info, sync_work_items_source_input):
        logger.info('SyncWorkItemsSource called')

        publish.sync_work_items_source_command(
            organization_key=sync_work_items_source_input.organization_key,
            work_items_source_key=sync_work_items_source_input.work_items_source_key
        )

        return SyncWorkItemsSource(
            success=True
        )


class ImportWorkItemsInput(graphene.InputObjectType):
    organization_key = graphene.String(required=True)
    work_items_source_key = graphene.String(required=True)
    source_ids = graphene.List(graphene.String)


class ImportWorkItems(graphene.Mutation):
    class Arguments:
        import_work_items_input = ImportWorkItemsInput(required=True)

    success = graphene.Boolean()
    error_message = graphene.String()

    def mutate(self, info, import_work_items_input):
        logger.info("Import work items called")
        if import_work_items_input.source_ids is not None:
            for source_id in import_work_items_input.source_ids:
                publish.import_work_item_command(
                    import_work_items_input.organization_key,
                    import_work_items_input.work_items_source_key,
                    source_id
                )
        else:
            publish.sync_work_items_source_command(
                import_work_items_input.organization_key,
                import_work_items_input.work_items_source_key
            )

        return ImportWorkItems(success=True)


class ResolveWorkItemsForProjectEpicsInput(graphene.InputObjectType):
    project_key = graphene.String(required=True)


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


class RegisterWebhooksInput(graphene.InputObjectType):
    connector_key = graphene.String(required=True)
    work_items_source_keys = graphene.List(graphene.String, required=True)


class WebhooksRegistrationStatus(graphene.ObjectType):
    work_items_source_key = graphene.String(required=True)
    success = graphene.Boolean(required=True)
    message = graphene.String(required=False)
    exception = graphene.String(required=False)


class RegisterWorkItemsSourcesConnectorWebhooks(graphene.Mutation):
    class Arguments:
        register_webhooks_input = RegisterWebhooksInput(required=True)

    webhooks_registration_status = graphene.List(WebhooksRegistrationStatus)

    def mutate(self, info, register_webhooks_input):
        connector_key = register_webhooks_input.connector_key
        work_items_source_keys = register_webhooks_input.work_items_source_keys

        logger.info(f'Register webhooks called for connector: {connector_key}')
        with db.orm_session() as session:
            result = commands.register_work_items_sources_webhooks(connector_key, work_items_source_keys,
                                                                   join_this=session)
            if result:
                return RegisterWorkItemsSourcesConnectorWebhooks(
                    webhooks_registration_status=[
                        WebhooksRegistrationStatus(
                            work_items_source_key=status.get('work_items_source_key'),
                            success=status.get('success'),
                            message=status.get('message'),
                            exception=status.get('exception')
                        )
                        for status in result]
                )


"""
For syncing the parameters of a work items source we are choosing to separate this out to several mutations
that each mutate related groups of parameters that are persisted in the json field of the work items source. 

This is because changing the parameters of work items source means that we have to reprocess history to reflect these parameters
in many cases and these are expensive operations where you need to do different things based on what parameters was changed. 

Also the changes are going to be localized in the UI as well so we will know where to invoke what mutation. 

OTOH having a single parameters blob for persistence means that this can be read by the connectors and api clients in a uniform fashion

So we are choosing to expose these as separate typed APIs for writes and as a single blob api for reads. 

This means more boiler plate code for the mutations, but it seems like a worthwhile trade off overall. 

"""


# Mutation to update sync parameters
class WorkItemsSourceSyncParameters(graphene.InputObjectType):
    initial_import_days = graphene.Int(required=False, description="Days of data to import on initial import")
    sync_import_days = graphene.Int(required=False, description="Days of data to import on subsequent sync operations")


class UpdateWorkItemsSourceSyncParametersInput(graphene.InputObjectType):
    organization_key = graphene.String(required=True)
    connector_key = graphene.String(required=True)
    work_items_source_keys = graphene.List(graphene.String, required=True)
    work_items_source_sync_parameters = WorkItemsSourceSyncParameters(required=True)


"""
Updates the sync parameters for the selected work items sources on the connector
and publishes a message to sync the work items source from the source system using these parameters. 

"""


class UpdateWorkItemsSourceSyncParameters(graphene.Mutation):
    class Arguments:
        update_work_items_source_sync_parameters_input = UpdateWorkItemsSourceSyncParametersInput(required=True)

    success = graphene.Boolean()
    error_message = graphene.String()
    updated = graphene.Int(description="The number of sources updated")

    def mutate(self, info, update_work_items_source_sync_parameters_input):
        organization_key = update_work_items_source_sync_parameters_input.organization_key
        connector_key = update_work_items_source_sync_parameters_input.connector_key
        work_items_source_keys = update_work_items_source_sync_parameters_input.work_items_source_keys
        work_items_source_parameters = update_work_items_source_sync_parameters_input.work_items_source_sync_parameters

        with db.orm_session() as session:
            result = api.update_work_items_source_parameters(connector_key, work_items_source_keys,
                                                             work_items_source_parameters, join_this=session)
            if result.get('success'):
                for work_items_source_key in work_items_source_keys:
                    publish.sync_work_items_source_command(organization_key, work_items_source_key)

        return UpdateWorkItemsSourceSyncParameters(
            success=result['success'],
            updated=result['updated']
        )


# Parent path selectors.

class WorkItemsSourceParentPathSelectors(graphene.InputObjectType):
    parent_path_selectors = graphene.List(graphene.String, required=False,
                                          description="""
                                        Array of jmespath expressions to select a parent key 
                                        from the json api payload for a work item fetched from this source.
                                        The expressions are evaluated in sequence and the value returned by the first
                                        non-null selector is used as the the parent key. The key here should be a user facing key
                                        and not the internal source identifier. 
                                        """)


class UpdateWorkItemsSourceParentPathSelectorsInput(graphene.InputObjectType):
    organization_key = graphene.String(required=True)
    connector_key = graphene.String(required=True)
    work_items_source_keys = graphene.List(graphene.String, required=True)
    work_items_source_parent_path_selectors = WorkItemsSourceParentPathSelectors(required=True)


class UpdateWorkItemsSourceParentPathSelectors(graphene.Mutation):
    class Arguments:
        update_work_items_source_parent_path_selectors_input = UpdateWorkItemsSourceParentPathSelectorsInput(
            required=True)

    success = graphene.Boolean()
    error_message = graphene.String()
    updated = graphene.Int(description="The number of sources updated")

    def mutate(self, info, update_work_items_source_parent_path_selectors_input):
        organization_key = update_work_items_source_parent_path_selectors_input.organization_key
        connector_key = update_work_items_source_parent_path_selectors_input.connector_key
        work_items_source_keys = update_work_items_source_parent_path_selectors_input.work_items_source_keys
        work_items_source_parameters = update_work_items_source_parent_path_selectors_input.work_items_source_parent_path_selectors

        with db.orm_session() as session:
            result = api.update_work_items_source_parameters(connector_key, work_items_source_keys,
                                                             work_items_source_parameters, join_this=session)
            if result.get('success'):
                for work_items_source_key in work_items_source_keys:
                    publish.parent_path_selectors_changed(organization_key, work_items_source_key)

        return UpdateWorkItemsSourceParentPathSelectors(
            success=result['success'],
            updated=result['updated']
        )


class PathSelectorMappingInput(graphene.InputObjectType):
    selector = graphene.String(required=True, description="""
                                        jmespathexpression that returns a value at a selected node in the input. 
                                        The tag is applied if the expression returns a non-null value
                                        """)
    value = graphene.String(required=False, description="Required when the mapping type is 'path-selector-value-equals")

    values = graphene.List(graphene.String, required=False,
                           description="Required when the mapping type is 'path-selector-value-in")

    tag = graphene.String(required=True, description="A tag of the form custom_tag:<tag> will be added to the tags")


class CustomFieldMappingInput(graphene.InputObjectType):
    field_name = graphene.String(required=True, description="""
                                        Name of the custom field. Must match exactly in the 
                                        associated meta data for custom fields
                                        """)
    tag = graphene.String(required=True, description="A tag of the form custom_tag:<tag> will be added to the tags")


class WorkItemsSourceCustomTagMappingItem(graphene.InputObjectType):
    # The types here must be one of the values in polaris.work_tracking.enums.CustomTagMapping
    mapping_type = graphene.String(required=True)
    # exactly one of these should be set in the input. The lack of union types in graphene inputs
    # forces us to use this awkward pattern,
    path_selector_mapping = PathSelectorMappingInput(required=False)
    custom_field_mapping = CustomFieldMappingInput(required=False)


class WorkItemsSourceCustomTagMapping(graphene.InputObjectType):
    custom_tag_mapping = graphene.List(
        WorkItemsSourceCustomTagMappingItem, required=True
    )


class UpdateWorkItemsSourceCustomTagMappingInput(graphene.InputObjectType):
    organization_key = graphene.String(required=True)
    connector_key = graphene.String(required=True)
    work_items_source_keys = graphene.List(graphene.String, required=True)
    work_items_source_custom_tag_mapping = WorkItemsSourceCustomTagMapping(required=True)


def validate_custom_tag_mapping(custom_tag_mapping):
    def validate_mapping_type(index, mapping, valid_mapping_types):
        if mapping.mapping_type not in valid_mapping_types:
            raise ProcessingException(
                f'Custom Tag Mapping at position {index} is invalid. Invalid Mapping type {mapping.mapping_type}. Must be one of {valid_mapping_types} ')

    def validate_path_selectors(index, mapping):
        if mapping.mapping_type in [
            CustomTagMappingType.path_selector.value,
            CustomTagMappingType.path_selector_false.value,
            CustomTagMappingType.path_selector_true.value,
            CustomTagMappingType.path_selector_value_equals.value,
            CustomTagMappingType.path_selector_value_in.value
        ]:
            try:
                jmespath.compile(mapping.path_selector_mapping.selector)
            except jmespath.exceptions.ParseError as e:
                raise ProcessingException(
                    f'Custom Tag Mapping at position {index} is invalid. Path selector {mapping.path_selector_mapping.selector} is an invalid jmespath expression {str(e)} ')

    def validate_path_selector_value_equals(index, mapping):
        if mapping.mapping_type == CustomTagMappingType.path_selector_value_equals.value:
            if mapping.path_selector_mapping.value is None:
                raise ProcessingException(f'Custom Tag Mapping at position {index} is invalid. '
                 f"Required attribute  'value' was not provided for mapping of type {CustomTagMappingType.path_selector_value_equals.value}")

    def validate_path_selector_value_in(index, mapping):
        if mapping.mapping_type == CustomTagMappingType.path_selector_value_in.value:
            if mapping.path_selector_mapping.values is None:
                raise ProcessingException(f'Custom Tag Mapping at position {index} is invalid. '
                 f"Required attribute  'values' was not provided for mapping of type {CustomTagMappingType.path_selector_value_in.value}")

    valid_mapping_types = [type.value for type in CustomTagMappingType]
    for index, mapping in enumerate(custom_tag_mapping):
        validate_mapping_type(index, mapping, valid_mapping_types)
        validate_path_selectors(index, mapping)
        validate_path_selector_value_equals(index, mapping)
        validate_path_selector_value_in(index, mapping)


class UpdateWorkItemsSourceCustomTagMapping(graphene.Mutation):
    class Arguments:
        update_work_items_source_custom_tag_mapping_input = UpdateWorkItemsSourceCustomTagMappingInput(required=True)

    success = graphene.Boolean()
    error_message = graphene.String()
    updated = graphene.Int(description="The number of sources updated")

    def mutate(self, info, update_work_items_source_custom_tag_mapping_input):
        organization_key = update_work_items_source_custom_tag_mapping_input.organization_key
        connector_key = update_work_items_source_custom_tag_mapping_input.connector_key
        work_items_source_keys = update_work_items_source_custom_tag_mapping_input.work_items_source_keys
        work_items_source_parameters = update_work_items_source_custom_tag_mapping_input.work_items_source_custom_tag_mapping

        validate_custom_tag_mapping(work_items_source_parameters.custom_tag_mapping)
        with db.orm_session() as session:
            result = api.update_work_items_source_parameters(connector_key, work_items_source_keys,
                                                             work_items_source_parameters, join_this=session)
            if result.get('success'):
                for work_items_source_key in work_items_source_keys:
                    publish.custom_tag_mapping_changed(organization_key, work_items_source_key)

        return UpdateWorkItemsSourceCustomTagMapping(
            success=result.get('success', False),
            updated=result.get('updated', 0)
        )

class ReprocessWorkItems(graphene.Mutation):
    class Arguments:
        reprocess_work_items_input = ReprocessWorkItemsInput(required=True)

    success = graphene.Boolean()

    def mutate(self, info, reprocess_work_items_input):
        logger.info("Reprocess Work Items called")

        publish.reprocess_work_items_command(organization_key=reprocess_work_items_input.organization_key,
            work_items_source_key=reprocess_work_items_input.work_items_source_key, attributes_to_check=reprocess_work_items_input.attributes_to_check
        )
        return ReprocessWorkItems(
            success=True
        )