# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal

import pytest
from unittest.mock import MagicMock, patch

from pika.channel import Channel

from polaris.messaging.message_consumer import MessageConsumer
from polaris.messaging.messages import WorkItemsCreated, WorkItemsUpdated
from polaris.work_tracking.messages import ResolveIssuesForEpic
from polaris.messaging.test_utils import mock_publisher, mock_channel, fake_send
from polaris.utils.token_provider import get_token_provider
from polaris.work_tracking.message_listener import WorkItemsTopicSubscriber
from polaris.messaging.topics import WorkItemsTopic
from polaris.utils.collections import object_to_dict
from ..fixtures.jira_fixtures import *
from test.constants import *
from datetime import datetime

mock_channel = MagicMock(Channel)
mock_consumer = MagicMock(MessageConsumer)
mock_consumer.token_provider = get_token_provider()

work_item_summary = dict(
    work_item_type=JiraWorkItemType.epic.value,
    description='Foo',
    is_bug=True,
    is_epic=True,
    tags=['acre'],
    last_updated=datetime.utcnow(),
    created_at=datetime.utcnow(),
    state='open'
)


@pytest.fixture()
def new_work_items_summary():
    return [
        dict(
            key=uuid.uuid4().hex,
            name=f'Issue {i}',
            source_id=str(i),
            display_id=str(i),
            url=f'http://foo.com/{i}',
            **work_item_summary
        )
        for i in range(100, 105)
    ]


class TestResolveIssuesForJiraEpic:

    def it_returns_valid_response_when_there_is_new_work_item_in_an_epic(self, jira_work_items_fixture, new_work_items,
                                                                         cleanup):
        work_items, work_items_source, jira_project_id, connector_key = jira_work_items_fixture
        new_mapped_work_item = new_work_items[0]
        with patch(
                'polaris.work_tracking.integrations.atlassian.jira_work_items_source.JiraProject.fetch_work_items_for_epic') as fetch_work_items_for_epic:
            fetch_work_items_for_epic.return_value = [[new_mapped_work_item]]
            epic_issue = [issue for issue in work_items if issue.is_epic][0]
            epic = object_to_dict(
                epic_issue,
                ['key',
                 'name',
                 'description',
                 'work_item_type',
                 'is_bug',
                 'is_epic',
                 'tags',
                 'source_id',
                 'source_display_id',
                 'source_state',
                 'url',
                 'source_created_at',
                 'source_last_updated',
                 'last_sync',
                 'epic_id'],
                {
                    'source_display_id': 'display_id',
                    'source_created_at': 'created_at',
                    'source_last_updated': 'last_updated',
                    'source_state': 'state',
                    'epic_id': 'epic_key'}
            )
            message = fake_send(
                ResolveIssuesForEpic(
                    send=dict(
                        organization_key=exathink_organization_key,
                        work_items_source_key=work_items_source.key,
                        epic=epic
                    )
                )
            )

            publisher = mock_publisher()
            channel = mock_channel()
            messages = WorkItemsTopicSubscriber(channel, publisher=publisher).dispatch(channel, message)
            assert len(messages) == 1
            publisher.assert_topic_called_with_message(WorkItemsTopic, WorkItemsCreated, call=0)

    def it_returns_valid_response_when_there_is_existing_work_item_in_an_epic(self, jira_work_items_fixture, cleanup):
        work_items, work_items_source, jira_project_id, connector_key = jira_work_items_fixture
        work_item_obj = [issue for issue in work_items if not issue.is_epic][0]
        mapped_work_item = object_to_dict(
            work_item_obj,
            ['name',
             'description',
             'work_item_type',
             'is_bug',
             'is_epic',
             'tags',
             'source_id',
             'source_display_id',
             'source_state',
             'url',
             'source_created_at',
             'source_last_updated'
             ]
        )
        with patch(
                'polaris.work_tracking.integrations.atlassian.jira_work_items_source.JiraProject.fetch_work_items_for_epic') as fetch_work_items_for_epic:
            fetch_work_items_for_epic.return_value = [[mapped_work_item]]
            epic_issue = [issue for issue in work_items if issue.is_epic][0]
            epic = object_to_dict(
                epic_issue,
                ['key',
                 'name',
                 'description',
                 'work_item_type',
                 'is_bug',
                 'is_epic',
                 'tags',
                 'source_id',
                 'source_display_id',
                 'source_state',
                 'url',
                 'source_created_at',
                 'source_last_updated',
                 'last_sync',
                 'epic_id'],
                {
                    'source_display_id': 'display_id',
                    'source_created_at': 'created_at',
                    'source_last_updated': 'last_updated',
                    'source_state': 'state',
                    'epic_id': 'epic_key'}
            )
            message = fake_send(
                ResolveIssuesForEpic(
                    send=dict(
                        organization_key=exathink_organization_key,
                        work_items_source_key=work_items_source.key,
                        epic=epic
                    )
                )
            )

            publisher = mock_publisher()
            channel = mock_channel()
            messages = WorkItemsTopicSubscriber(channel, publisher=publisher).dispatch(channel, message)
            assert len(messages) == 1
            publisher.assert_topic_called_with_message(WorkItemsTopic, WorkItemsUpdated, call=0)

    def it_returns_valid_responses_when_there_are_new_and_existing_work_items_in_an_epic(self, jira_work_items_fixture,
                                                                                         new_work_items, cleanup):
        work_items, work_items_source, jira_project_id, connector_key = jira_work_items_fixture
        work_item_obj = [issue for issue in work_items if not issue.is_epic][0]
        mapped_work_item = object_to_dict(
            work_item_obj,
            ['name',
             'description',
             'work_item_type',
             'is_bug',
             'is_epic',
             'tags',
             'source_id',
             'source_display_id',
             'source_state',
             'url',
             'source_created_at',
             'source_last_updated'
             ]
        )
        new_mapped_work_item = new_work_items[0]
        with patch(
                'polaris.work_tracking.integrations.atlassian.jira_work_items_source.JiraProject.fetch_work_items_for_epic') as fetch_work_items_for_epic:
            fetch_work_items_for_epic.return_value = [[mapped_work_item, new_mapped_work_item]]
            epic_issue = [issue for issue in work_items if issue.is_epic][0]
            epic = object_to_dict(
                epic_issue,
                ['key',
                 'name',
                 'description',
                 'work_item_type',
                 'is_bug',
                 'is_epic',
                 'tags',
                 'source_id',
                 'source_display_id',
                 'source_state',
                 'url',
                 'source_created_at',
                 'source_last_updated',
                 'last_sync',
                 'epic_id'],
                {
                    'source_display_id': 'display_id',
                    'source_created_at': 'created_at',
                    'source_last_updated': 'last_updated',
                    'source_state': 'state',
                    'epic_id': 'epic_key'}
            )
            message = fake_send(
                ResolveIssuesForEpic(
                    send=dict(
                        organization_key=exathink_organization_key,
                        work_items_source_key=work_items_source.key,
                        epic=epic
                    )
                )
            )

            publisher = mock_publisher()
            channel = mock_channel()
            messages = WorkItemsTopicSubscriber(channel, publisher=publisher).dispatch(channel, message)
            assert len(messages) == 2
            publisher.assert_topic_called_with_message(WorkItemsTopic, WorkItemsCreated, call=0)
            publisher.assert_topic_called_with_message(WorkItemsTopic, WorkItemsUpdated, call=1)

    def it_returns_no_response_when_there_is_no_work_item_in_an_epic(self, jira_work_items_fixture, new_work_items,
                                                                     cleanup):
        work_items, work_items_source, jira_project_id, connector_key = jira_work_items_fixture
        with patch(
                'polaris.work_tracking.integrations.atlassian.jira_work_items_source.JiraProject.fetch_work_items_for_epic') as fetch_work_items_for_epic:
            fetch_work_items_for_epic.return_value = [[]]
            epic_issue = [issue for issue in work_items if issue.is_epic][0]
            epic = object_to_dict(
                epic_issue,
                ['key',
                 'name',
                 'description',
                 'work_item_type',
                 'is_bug',
                 'is_epic',
                 'tags',
                 'source_id',
                 'source_display_id',
                 'source_state',
                 'url',
                 'source_created_at',
                 'source_last_updated',
                 'last_sync',
                 'epic_id'],
                {
                    'source_display_id': 'display_id',
                    'source_created_at': 'created_at',
                    'source_last_updated': 'last_updated',
                    'source_state': 'state',
                    'epic_id': 'epic_key'}
            )
            message = fake_send(
                ResolveIssuesForEpic(
                    send=dict(
                        organization_key=exathink_organization_key,
                        work_items_source_key=work_items_source.key,
                        epic=epic
                    )
                )
            )

            publisher = mock_publisher()
            channel = mock_channel()
            messages = WorkItemsTopicSubscriber(channel, publisher=publisher).dispatch(channel, message)
            assert len(messages) == 0
