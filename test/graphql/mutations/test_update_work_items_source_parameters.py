# -*- coding: utf-8 -*-

#  Copyright (c) Exathink, LLC  2016-2023.
#  All rights reserved
#

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import pytest
from unittest.mock import patch
from graphene.test import Client
from polaris.common import db
from polaris.messaging.test_utils import assert_topic_and_message
from polaris.messaging.topics import WorkItemsTopic
from polaris.messaging.messages import ImportWorkItems
from polaris.work_tracking.messages import ParentPathSelectorsChanged

from polaris.work_tracking.db.model import WorkItemsSource
from polaris.work_tracking.messages.work_items_source_parameters_changed import CustomTagMappingChanged
from polaris.work_tracking.service.graphql import schema

from test.fixtures.jira_fixtures import *


class TestUpdateWorkItemsSourceParameters(WorkItemsSourceTest):
    class TestUpdateSyncParameters:

        def it_creates_the_parameters_for_the_first_time(self, setup):
            fixture = setup
            organization_key = fixture.organization_key
            work_items_source = fixture.work_items_source
            connector_key = fixture.connector_key

            client = Client(schema)
            mutation = """
                mutation updateWorkItemsSourceSyncParameters(
                    $updateWorkItemsSourceSyncParametersInput: UpdateWorkItemsSourceSyncParametersInput! 
                    ) {
                        updateWorkItemsSourceSyncParameters(updateWorkItemsSourceSyncParametersInput: $updateWorkItemsSourceSyncParametersInput) {
                            success
                            errorMessage
                            updated
                        }
                    } 
            """
            with patch('polaris.work_tracking.publish.publish'):
                result = client.execute(mutation, variable_values=dict(
                    updateWorkItemsSourceSyncParametersInput=dict(
                        organizationKey=organization_key,
                        connectorKey=str(connector_key),
                        workItemsSourceKeys=[
                            str(work_items_source.key)
                        ],
                        workItemsSourceSyncParameters=dict(
                            initialImportDays=180,
                            syncImportDays=7,
                        )
                    )))
            assert result.get('errors') is None
            assert result['data']['updateWorkItemsSourceSyncParameters']['success']
            assert result['data']['updateWorkItemsSourceSyncParameters']['updated'] == 1

            with db.orm_session() as session:
                source = WorkItemsSource.find_by_key(session, work_items_source.key)
                assert source.parameters == dict(
                    initial_import_days=180,
                    sync_import_days=7,

                )

        def it_only_updates_the_entries_that_are_passed_in(self, setup):
            fixture = setup
            organization_key = fixture.organization_key
            work_items_source = fixture.work_items_source
            connector_key = fixture.connector_key

            with db.orm_session() as session:
                session.add(work_items_source)
                work_items_source.parameters = dict(
                    initial_import_days=180,
                    sync_import_days=7
                )

            client = Client(schema)
            mutation = """
                mutation updateWorkItemsSourceParameters(
                    $updateWorkItemsSourceSyncParametersInput: UpdateWorkItemsSourceSyncParametersInput! 
                    ) {
                        updateWorkItemsSourceSyncParameters(updateWorkItemsSourceSyncParametersInput: $updateWorkItemsSourceSyncParametersInput) {
                            success
                            errorMessage
                            updated
                        }
                    } 
            """
            with patch('polaris.work_tracking.publish.publish'):
                result = client.execute(mutation, variable_values=dict(
                    updateWorkItemsSourceSyncParametersInput=dict(
                        organizationKey=organization_key,
                        connectorKey=str(connector_key),
                        workItemsSourceKeys=[
                            str(work_items_source.key)
                        ],
                        workItemsSourceSyncParameters=dict(
                            syncImportDays=30
                        )
                    )))

            assert result.get('errors') is None
            assert result['data']['updateWorkItemsSourceSyncParameters']['success']
            assert result['data']['updateWorkItemsSourceSyncParameters']['updated'] == 1

            with db.orm_session() as session:
                source = WorkItemsSource.find_by_key(session, work_items_source.key)
                assert source.parameters == dict(
                    initial_import_days=180,
                    sync_import_days=30,
                )

        def it_publishes_the_sync_work_items_message(self, setup):
            fixture = setup
            organization_key = fixture.organization_key
            work_items_source = fixture.work_items_source
            connector_key = fixture.connector_key

            with db.orm_session() as session:
                session.add(work_items_source)
                work_items_source.parameters = dict(
                    initial_import_days=180,
                    sync_import_days=7
                )

            client = Client(schema)
            mutation = """
                mutation updateWorkItemsSourceParameters(
                    $updateWorkItemsSourceSyncParametersInput: UpdateWorkItemsSourceSyncParametersInput! 
                    ) {
                        updateWorkItemsSourceSyncParameters(updateWorkItemsSourceSyncParametersInput: $updateWorkItemsSourceSyncParametersInput) {
                            success
                            errorMessage
                            updated
                        }
                    } 
            """
            with patch('polaris.work_tracking.publish.publish') as publish:
                result = client.execute(mutation, variable_values=dict(
                    updateWorkItemsSourceSyncParametersInput=dict(
                        organizationKey=organization_key,
                        connectorKey=str(connector_key),
                        workItemsSourceKeys=[
                            str(work_items_source.key)
                        ],
                        workItemsSourceSyncParameters=dict(
                            syncImportDays=30
                        )
                    )))

            assert result.get('errors') is None
            assert result['data']['updateWorkItemsSourceSyncParameters']['success']
            assert result['data']['updateWorkItemsSourceSyncParameters']['updated'] == 1

            assert_topic_and_message(publish, WorkItemsTopic, ImportWorkItems)

    class TestUpdateParentPathSelectors:

        def it_creates_the_parameters_for_the_first_time(self, setup):
            fixture = setup
            organization_key = fixture.organization_key
            work_items_source = fixture.work_items_source
            connector_key = fixture.connector_key

            client = Client(schema)
            mutation = """
                mutation updateWorkItemsSourceParentPathSelectors(
                    $updateWorkItemsSourceParentPathSelectorsInput: UpdateWorkItemsSourceParentPathSelectorsInput! 
                    ) {
                        updateWorkItemsSourceParentPathSelectors(updateWorkItemsSourceParentPathSelectorsInput: $updateWorkItemsSourceParentPathSelectorsInput) {
                            success
                            errorMessage
                            updated
                        }
                    } 
            """
            with patch('polaris.work_tracking.publish.publish'):
                result = client.execute(mutation, variable_values=dict(
                    updateWorkItemsSourceParentPathSelectorsInput=dict(
                        organizationKey=organization_key,
                        connectorKey=str(connector_key),
                        workItemsSourceKeys=[
                            str(work_items_source.key)
                        ],
                        workItemsSourceParentPathSelectors=dict(
                            parentPathSelectors=[
                                "(fields.issuelinks[?(type.name=='Parent/Child' && outwardIssue.fields.issuetype.name=='Feature')].outwardIssue.key)[0]"
                            ]
                        )
                    )))
            assert result.get('errors') is None
            assert result['data']['updateWorkItemsSourceParentPathSelectors']['success']
            assert result['data']['updateWorkItemsSourceParentPathSelectors']['updated'] == 1

            with db.orm_session() as session:
                source = WorkItemsSource.find_by_key(session, work_items_source.key)
                assert source.parameters == dict(
                    parent_path_selectors=[
                        "(fields.issuelinks[?(type.name=='Parent/Child' && outwardIssue.fields.issuetype.name=='Feature')].outwardIssue.key)[0]"
                    ]

                )

        def it_only_updates_the_parent_path_selectors(self, setup):
            fixture = setup
            organization_key = fixture.organization_key
            work_items_source = fixture.work_items_source
            connector_key = fixture.connector_key

            with db.orm_session() as session:
                session.add(work_items_source)
                work_items_source.parameters = dict(
                    initial_import_days=180,
                    sync_import_days=7
                )

            client = Client(schema)
            mutation = """
                mutation updateWorkItemsSourceParentPathSelectors(
                    $updateWorkItemsSourceParentPathSelectorsInput: UpdateWorkItemsSourceParentPathSelectorsInput! 
                    ) {
                        updateWorkItemsSourceParentPathSelectors(updateWorkItemsSourceParentPathSelectorsInput: $updateWorkItemsSourceParentPathSelectorsInput) {
                            success
                            errorMessage
                            updated
                        }
                    } 
            """
            with patch('polaris.work_tracking.publish.publish'):
                result = client.execute(mutation, variable_values=dict(
                    updateWorkItemsSourceParentPathSelectorsInput=dict(
                        organizationKey=organization_key,
                        connectorKey=str(connector_key),
                        workItemsSourceKeys=[
                            str(work_items_source.key)
                        ],
                        workItemsSourceParentPathSelectors=dict(
                            parentPathSelectors=[
                                "(fields.issuelinks[?(type.name=='Parent/Child' && outwardIssue.fields.issuetype.name=='Feature')].outwardIssue.key)[0]"
                            ]
                        )
                    )))
            assert result.get('errors') is None
            assert result['data']['updateWorkItemsSourceParentPathSelectors']['success']
            assert result['data']['updateWorkItemsSourceParentPathSelectors']['updated'] == 1

            with db.orm_session() as session:
                source = WorkItemsSource.find_by_key(session, work_items_source.key)
                assert source.parameters == dict(
                    initial_import_days=180,
                    sync_import_days=7,
                    parent_path_selectors=[
                        "(fields.issuelinks[?(type.name=='Parent/Child' && outwardIssue.fields.issuetype.name=='Feature')].outwardIssue.key)[0]"
                    ]

                )

        def it_publishes_parent_path_selectors_changed_message(self, setup):
            fixture = setup
            organization_key = fixture.organization_key
            work_items_source = fixture.work_items_source
            connector_key = fixture.connector_key

            with db.orm_session() as session:
                session.add(work_items_source)
                work_items_source.parameters = dict(
                    initial_import_days=180,
                    sync_import_days=7
                )

            client = Client(schema)
            mutation = """
                mutation updateWorkItemsSourceParentPathSelectors(
                    $updateWorkItemsSourceParentPathSelectorsInput: UpdateWorkItemsSourceParentPathSelectorsInput! 
                    ) {
                        updateWorkItemsSourceParentPathSelectors(updateWorkItemsSourceParentPathSelectorsInput: $updateWorkItemsSourceParentPathSelectorsInput) {
                            success
                            errorMessage
                            updated
                        }
                    } 
            """
            with patch('polaris.work_tracking.publish.publish') as publish:
                result = client.execute(mutation, variable_values=dict(
                    updateWorkItemsSourceParentPathSelectorsInput=dict(
                        organizationKey=organization_key,
                        connectorKey=str(connector_key),
                        workItemsSourceKeys=[
                            str(work_items_source.key)
                        ],
                        workItemsSourceParentPathSelectors=dict(
                            parentPathSelectors=[
                                "(fields.issuelinks[?(type.name=='Parent/Child' && outwardIssue.fields.issuetype.name=='Feature')].outwardIssue.key)[0]"
                            ]
                        )
                    )))
            assert result.get('errors') is None
            assert result['data']['updateWorkItemsSourceParentPathSelectors']['success']
            assert result['data']['updateWorkItemsSourceParentPathSelectors']['updated'] == 1

            assert_topic_and_message(publish, WorkItemsTopic, ParentPathSelectorsChanged)

    class TestUpdateCustomTagMapping:

        def it_creates_a_selector_to_tag_mapping(self, setup):
            fixture = setup
            organization_key = fixture.organization_key
            work_items_source = fixture.work_items_source
            connector_key = fixture.connector_key

            client = Client(schema)
            mutation = """
                mutation updateWorkItemsSourceCustomTagMapping(
                    $updateWorkItemsSourceCustomTagMappingInput: UpdateWorkItemsSourceCustomTagMappingInput! 
                    ) {
                        updateWorkItemsSourceCustomTagMapping(updateWorkItemsSourceCustomTagMappingInput: $updateWorkItemsSourceCustomTagMappingInput) {
                            success
                            errorMessage
                            updated
                        }
                    } 
            """
            with patch('polaris.work_tracking.publish.publish'):
                result = client.execute(mutation, variable_values=dict(
                    updateWorkItemsSourceCustomTagMappingInput=dict(
                        organizationKey=organization_key,
                        connectorKey=str(connector_key),
                        workItemsSourceKeys=[
                            str(work_items_source.key)
                        ],
                        workItemsSourceCustomTagMapping=dict(
                          customTagMapping= [
                              dict(
                                mappingType='path-selector',
                                pathSelectorMapping=dict(
                                    selector="((fields.issuelinks[?type.name=='Parent/Child'])[?outwardIssue.fields.issuetype.name == 'Feature'])[0]",
                                    tag="feature-item"
                                )
                            )]
                        )
                    )))
            assert result.get('errors') is None
            assert result['data']['updateWorkItemsSourceCustomTagMapping']['success']
            assert result['data']['updateWorkItemsSourceCustomTagMapping']['updated'] == 1

            with db.orm_session() as session:
                source = WorkItemsSource.find_by_key(session, work_items_source.key)
                assert source.parameters == dict(
                    custom_tag_mapping=[
                        dict(
                            mapping_type='path-selector',
                            path_selector_mapping = dict(
                                selector="((fields.issuelinks[?type.name=='Parent/Child'])[?outwardIssue.fields.issuetype.name == 'Feature'])[0]",
                                tag="feature-item"
                            )
                        )
                    ]
                )

        def it_publishes_the_custom_tag_mapping_changed_message(self, setup):
            fixture = setup
            organization_key = fixture.organization_key
            work_items_source = fixture.work_items_source
            connector_key = fixture.connector_key

            client = Client(schema)
            mutation = """
                mutation updateWorkItemsSourceCustomTagMapping(
                    $updateWorkItemsSourceCustomTagMappingInput: UpdateWorkItemsSourceCustomTagMappingInput! 
                    ) {
                        updateWorkItemsSourceCustomTagMapping(updateWorkItemsSourceCustomTagMappingInput: $updateWorkItemsSourceCustomTagMappingInput) {
                            success
                            errorMessage
                            updated
                        }
                    } 
            """
            with patch('polaris.work_tracking.publish.publish') as publish:
                result = client.execute(mutation, variable_values=dict(
                    updateWorkItemsSourceCustomTagMappingInput=dict(
                        organizationKey=organization_key,
                        connectorKey=str(connector_key),
                        workItemsSourceKeys=[
                            str(work_items_source.key)
                        ],
                        workItemsSourceCustomTagMapping=dict(
                          customTagMapping= [
                              dict(
                                mappingType='path-selector',
                                pathSelectorMapping=dict(
                                    selector="((fields.issuelinks[?type.name=='Parent/Child'])[?outwardIssue.fields.issuetype.name == 'Feature'])[0]",
                                    tag="feature-item"
                                )
                            )]
                        )
                    )))
            assert result.get('errors') is None
            assert_topic_and_message(publish, WorkItemsTopic, CustomTagMappingChanged)
