# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal

import pytest
from unittest.mock import MagicMock

from pika.channel import Channel

from polaris.messaging.message_consumer import MessageConsumer
from polaris.messaging.messages import WorkItemsCreated, WorkItemsUpdated
from polaris.work_tracking.messages import ResolveIssuesForEpic
from polaris.messaging.test_utils import mock_publisher, mock_channel, fake_send
from polaris.utils.token_provider import get_token_provider
from polaris.work_tracking.message_listener import WorkItemsTopicSubscriber
from polaris.messaging.topics import WorkItemsTopic
from polaris.utils.collections import dict_merge, dict_drop
from polaris.common.enums import JiraWorkItemType
from test.constants import *
from datetime import datetime

mock_channel = MagicMock(Channel)
mock_consumer = MagicMock(MessageConsumer)
mock_consumer.token_provider = get_token_provider()
jira_work_items_source_key = uuid.uuid4().hex

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



class TestJiraWorkItemsUpdated:

    def it_publishes_a_response_when_there_is_an_epic_in_work_items(self, new_work_items_summary, cleanup):
        work_items = new_work_items_summary
        message = fake_send(
            WorkItemsUpdated(
                send=dict(
                    organization_key=exathink_organization_key,
                    work_items_source_key=jira_work_items_source_key,
                    updated_work_items=[
                        dict_merge(
                            dict_drop(work_item, ['epic_id']),
                            dict(epic_key=None)
                        )
                        for work_item in work_items
                    ]
                )
            )
        )
        publisher = mock_publisher()
        channel = mock_channel()

        result = WorkItemsTopicSubscriber(channel, publisher=publisher).dispatch(channel, message)
        assert len(result) == len(work_items)
        publisher.assert_topic_called_with_message(WorkItemsTopic, ResolveIssuesForEpic, call=0)
        publisher.assert_topic_called_with_message(WorkItemsTopic, ResolveIssuesForEpic, call=1)
        publisher.assert_topic_called_with_message(WorkItemsTopic, ResolveIssuesForEpic, call=2)
        publisher.assert_topic_called_with_message(WorkItemsTopic, ResolveIssuesForEpic, call=3)
        publisher.assert_topic_called_with_message(WorkItemsTopic, ResolveIssuesForEpic, call=4)

    def it_does_not_publish_response_when_there_is_no_epic(self, new_work_items_summary, cleanup):
        work_items = new_work_items_summary
        message = fake_send(
            WorkItemsUpdated(
                send=dict(
                    organization_key=exathink_organization_key,
                    work_items_source_key=jira_work_items_source_key,
                    updated_work_items=[
                        dict_merge(
                            dict_drop(work_item, ['epic_id']),
                            dict(epic_key=None, is_epic=False)
                        )
                        for work_item in work_items
                    ]
                )
            )
        )
        publisher = mock_publisher()
        channel = mock_channel()

        result = WorkItemsTopicSubscriber(channel, publisher=publisher).dispatch(channel, message)
        assert len(result) == 0


