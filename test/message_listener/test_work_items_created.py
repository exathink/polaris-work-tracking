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
from polaris.messaging.messages import WorkItemsCreated, WorkItemsUpdated, ImportWorkItem
from polaris.work_tracking.messages import ResolveWorkItemsForEpic
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
    state='open',
    priority='Medium'
)


@pytest.fixture()
def new_work_items_summary():
    return [
        dict(
            key=uuid.uuid4().hex,
            name=f'Issue {i}',
            source_id=str(i),
            display_id=str(i),
            parent_source_display_id=None,
            url=f'http://foo.com/{i}',
            **work_item_summary
        )
        for i in range(100, 105)
    ]


class TestJiraWorkItemsCreated:



    def it_publishes_import_work_item_message_when_a_missing_parent_needs_to_be_imported(self, new_work_items_summary,
                                                                                         cleanup):
        work_items = new_work_items_summary
        message = fake_send(
            WorkItemsCreated(
                send=dict(
                    organization_key=exathink_organization_key,
                    work_items_source_key=jira_work_items_source_key,
                    new_work_items=[
                        dict_merge(
                            dict_drop(work_item, ['parent_id']),
                            dict(parent_source_display_id='Epic-123', is_epic=False, parent_key=None)
                        )
                        for work_item in work_items
                    ]
                )
            )
        )
        publisher = mock_publisher()
        channel = mock_channel()

        result = WorkItemsTopicSubscriber(channel, publisher=publisher).dispatch(channel, message)
        assert len(result) == 1
        publisher.assert_topic_called_with_message(WorkItemsTopic, ImportWorkItem)


    def it_sends_all_fields_to_analytics(self, new_work_items_summary):
        field_list = [
            "key",
            "display_id",
            "work_item_type",
            "url",
            "name",
            "is_bug",
            "tags",
            "state",
            "created_at",
            "description",
            "source_id",
            "is_epic",
            "parent_source_display_id",
            "priority"
        ]
        work_items = new_work_items_summary
        message = fake_send(
            WorkItemsCreated(
                send=dict(
                    organization_key=exathink_organization_key,
                    work_items_source_key=jira_work_items_source_key,
                    new_work_items=[
                        dict_merge(
                            dict_drop(work_item, ['parent_id']),
                            dict(parent_source_display_id='Epic-123', is_epic=False, parent_key=None)
                        )
                        for work_item in work_items
                    ]
                )
            )
        )
        for work_item in message['new_work_items']:
            for field in field_list:
                assert field in work_item

