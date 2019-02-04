# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from unittest.mock import patch
from graphene.test import Client
from polaris.work_tracking.service.graphql import schema
from polaris.messaging.topics import WorkItemsTopic
from polaris.messaging.messages import WorkItemsSourceCreated
from polaris.messaging.test_utils import assert_topic_and_message


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
