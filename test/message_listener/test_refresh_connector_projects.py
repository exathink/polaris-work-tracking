# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal

from unittest.mock import patch, MagicMock

from pika.channel import Channel

from polaris.messaging.message_consumer import MessageConsumer
from polaris.work_tracking.messages import RefreshConnectorProjects
from polaris.messaging.test_utils import mock_publisher, mock_channel, assert_topic_and_message, fake_send
from polaris.utils.token_provider import get_token_provider
from polaris.work_tracking.message_listener import ConnectorsTopicSubscriber
from polaris.messaging.topics import WorkItemsTopic
from polaris.messaging.messages import WorkItemsSourceCreated
from polaris.common.enums import WorkTrackingIntegrationType
from polaris.work_tracking.integrations.gitlab import GitlabWorkItemSourceType

mock_channel = MagicMock(Channel)
mock_consumer = MagicMock(MessageConsumer)
mock_consumer.token_provider = get_token_provider()


class TestConnectorsTopicSubscriber:
    class TestRefreshConnectorProjects:

        def it_returns_a_valid_response_when_projects_are_refreshed(self, setup_connectors):
            project = {
                'id': 24543756,
                'description': '',
                'name': 'Exathink Alliance Test',
                'path': 'exathink-alliance-test',
                'path_with_namespace': 'gitlab-com/alliances/exathink/sandbox-projects/exathink-alliance-test',
                'created_at': '2021-02-20T01:19:34.978Z',
                'default_branch': 'master',
                'tag_list': [],
                '_links': {
                    'self': 'https://gitlab.com/api/v4/projects/24543756',
                    'issues': 'https://gitlab.com/api/v4/projects/24543756/issues',
                    'merge_requests': 'https://gitlab.com/api/v4/projects/24543756/merge_requests',
                    'repo_branches': 'https://gitlab.com/api/v4/projects/24543756/repository/branches',
                    'labels': 'https://gitlab.com/api/v4/projects/24543756/labels',
                    'events': 'https://gitlab.com/api/v4/projects/24543756/events',
                    'members': 'https://gitlab.com/api/v4/projects/24543756/members'
                }
            }

            connector_keys = setup_connectors
            gitlab_connector_key = connector_keys['gitlab']
            with patch(
                    'polaris.work_tracking.integrations.gitlab.gitlab_connector.GitlabWorkTrackingConnector.fetch_work_items_sources_to_sync') as fetch_work_items_sources_to_sync:
                fetch_work_items_sources_to_sync.return_value = [[
                    dict(
                        integration_type=WorkTrackingIntegrationType.gitlab.value,
                        work_items_source_type=GitlabWorkItemSourceType.projects.value,
                        parameters=dict(
                            repository=project['name']
                        ),
                        commit_mapping_scope='repository',
                        source_id=project['id'],
                        name=project['name'],
                        url=project["_links"]['issues'],
                        description=project['description'],
                        custom_fields=[],
                        source_data={},
                        source_states=[]
                    )]]

                refresh_connector_projects_message = fake_send(
                    RefreshConnectorProjects(send=dict(
                        connector_key=gitlab_connector_key,
                    ))
                )

                publisher = mock_publisher()
                subscriber = ConnectorsTopicSubscriber(mock_channel, publisher=publisher)
                subscriber.consumer_context = mock_consumer

                messages = subscriber.dispatch(mock_channel, refresh_connector_projects_message)
                assert len(messages) == 2
                publisher.assert_topic_called_with_message(WorkItemsTopic, WorkItemsSourceCreated, call=0)
