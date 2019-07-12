# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar
import pytest
import uuid
from unittest.mock import patch
from graphene.test import Client
from polaris.work_tracking.service.graphql import schema
from polaris.messaging.topics import WorkItemsTopic
from polaris.messaging.messages import WorkItemsSourceCreated
from polaris.messaging.test_utils import assert_topic_and_message
from polaris.common.enums import WorkItemsSourceImportState
from polaris.common import db
from polaris.work_tracking.db import model

from test.constants import *


class TestCreateWorkItemSource:

    def it_creates_a_pivotal_source(self, setup_schema):
        client = Client(schema)
        with patch('polaris.work_tracking.publish.work_items_source_created'):
            response = client.execute("""
                mutation createWorkItemsSource {
                        createWorkItemsSource(
                            data:{
                                accountKey: "3a0480a3-2eb8-4728-987f-674cbe3cf48c",
                                organizationKey:"8850852b-9187-4284-bb1f-98ea89ae31fe",
                                commitMappingScope:organization,
                                commitMappingScopeKey: "8850852b-9187-4284-bb1f-98ea89ae31fe",
                                integrationType: pivotal,
                                name: "polaris-web",
                                pivotalParameters:{
                                    workItemsSourceType: project,
                                    name: "polaris-web",
                                    id: "1934657"
                                }
                            }                     
                        ) 
                {
                    name
                    key
                }
            }
            """)
            result = response['data']['createWorkItemsSource']
            assert result
            assert result['key']
            assert result['name'] == 'polaris-web'

    def it_creates_a_github_source(self, setup_schema):
        client = Client(schema)
        with patch('polaris.work_tracking.publish.work_items_source_created'):
            response = client.execute("""
                mutation createWorkItemsSource {
                        createWorkItemsSource(
                            data:{
                                accountKey: "3a0480a3-2eb8-4728-987f-674cbe3cf48c",
                                organizationKey:"8850852b-9187-4284-bb1f-98ea89ae31fe",
                                commitMappingScope:organization,
                                commitMappingScopeKey: "8850852b-9187-4284-bb1f-98ea89ae31fe",
                                integrationType: github,
                                name: "rails",
                                githubParameters:{
                                    workItemsSourceType: repository_issues,
                                    organization: "rails",
                                    repository: "rails",
                                    bugTags: ["With reproduction steps"]
                                }
                            }                     
                        ) 
                {
                    name
                    key
                }
            }
            """)
            result = response['data']['createWorkItemsSource']
            assert result
            assert result['key']
            assert result['name'] == 'rails'

    def it_publishes_the_notification_correctly(self, setup_schema):
        client = Client(schema)
        with patch('polaris.work_tracking.publish.publish') as publish:
            response = client.execute("""
                mutation createWorkItemsSource {
                        createWorkItemsSource(
                            data:{
                                accountKey: "3a0480a3-2eb8-4728-987f-674cbe3cf48c",
                                organizationKey:"8850852b-9187-4284-bb1f-98ea89ae31fe",
                                commitMappingScope:organization,
                                commitMappingScopeKey: "8850852b-9187-4284-bb1f-98ea89ae31fe",
                                integrationType: github,
                                name: "rails",
                                githubParameters:{
                                    workItemsSourceType: repository_issues,
                                    organization: "rails",
                                    repository: "rails",
                                    bugTags: ["With reproduction steps"]
                                }
                            }                     
                        ) 
                {
                    name
                    key
                }
            }
            """)
            publish.assert_called()
            assert_topic_and_message(publish, WorkItemsTopic, WorkItemsSourceCreated)


@pytest.yield_fixture
def setup_attached_and_unattached_work_items_sources(setup_connectors):
    connector_keys = setup_connectors
    with db.orm_session() as session:
        # Pivotal connector will have no attached work items sources. This should be deleted on delete
        unattached_work_items_source = model.WorkItemsSource(
            key=uuid.uuid4(),
            connector_key=connector_keys['pivotal'],
            integration_type='pivotal_tracker',
            work_items_source_type='project',
            parameters=dict(id="1934657", name="polaris-web"),
            name='polaris-web',
            account_key=exathink_account_key,
            organization_key=polaris_organization_key,
            commit_mapping_scope='organization',
            commit_mapping_scope_key=polaris_organization_key,
            import_state=WorkItemsSourceImportState.ready.value
        )
        session.add(unattached_work_items_source)

        # github connector will have one attached work items source. This should be archived on delete
        project = model.Project(
            name='TestProject',
            key=uuid.uuid4(),
            organization_key=polaris_organization_key,
            account_key=exathink_account_key
        )

        project.work_items_sources.append(
            model.WorkItemsSource(
                key=uuid.uuid4(),
                integration_type='github',
                connector_key=connector_keys['github'],
                work_items_source_type='repository_issues',
                parameters=dict(repository='rails', organization='rails'),
                name='rails repository issues',
                account_key=exathink_account_key,
                organization_key=rails_organization_key,
                commit_mapping_scope='organization',
                commit_mapping_scope_key=rails_organization_key,
                import_state=WorkItemsSourceImportState.ready.value
            )
        )
        session.add(project)

        session.flush()
        yield connector_keys


class TestDeleteWorkTrackingConnector:

    def it_deletes_the_connector_if_there_all_work_items_sources_are_unattached(self,
                                                                                setup_attached_and_unattached_work_items_sources, cleanup):
        connector_keys = setup_attached_and_unattached_work_items_sources
        unattached_connector_key = connector_keys['pivotal']

        client = Client(schema)

        response = client.execute("""
                        mutation deleteConnector($connectorKey: String!){
                                deleteConnector(
                                    deleteConnectorInput:{
                                        connectorKey: $connectorKey
                                    }
                                ) {
                                    connectorName
                                    disposition
                                }
                        }
                        """,
                          variable_values=dict(
                              connectorKey=unattached_connector_key
                          ))
        assert response['data']['deleteConnector']
        assert response['data']['deleteConnector']['connectorName']
        assert response['data']['deleteConnector']['disposition'] == 'deleted'

        assert db.connection().execute(f"select count(id) from integrations.connectors where key='{unattached_connector_key}'").scalar() == 0

    def it_archives_the_connector_if_there_are_attached_work_items_sources(self,
                                                                                setup_attached_and_unattached_work_items_sources):
        connector_keys = setup_attached_and_unattached_work_items_sources
        attached_connector_key = connector_keys['github']

        client = Client(schema)

        response = client.execute("""
                        mutation deleteConnector($connectorKey: String!){
                                deleteConnector(
                                    deleteConnectorInput:{
                                        connectorKey: $connectorKey
                                    }
                                ) {
                                    connectorName
                                    disposition
                                }
                        }
                        """,
                          variable_values=dict(
                              connectorKey=attached_connector_key
                          ))
        assert response['data']['deleteConnector']
        assert response['data']['deleteConnector']['connectorName']
        assert response['data']['deleteConnector']['disposition'] == 'archived'

        assert db.connection().execute(
            f"select archived from integrations.connectors where key='{attached_connector_key}'").scalar()