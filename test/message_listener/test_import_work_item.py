# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from unittest.mock import patch, MagicMock

from pika.channel import Channel

from polaris.messaging.message_consumer import MessageConsumer
from polaris.messaging.messages import \
    ImportWorkItem, WorkItemsCreated, WorkItemsUpdated
from polaris.messaging.test_utils import mock_publisher, mock_channel, assert_topic_and_message, fake_send
from polaris.utils.token_provider import get_token_provider
from polaris.work_tracking.message_listener import WorkItemsTopicSubscriber
from polaris.messaging.topics import WorkItemsTopic
from polaris.utils.exceptions import ProcessingException

from test.constants import *
from ..fixtures.jira_fixtures import *

mock_channel = MagicMock(Channel)
mock_consumer = MagicMock(MessageConsumer)
mock_consumer.token_provider = get_token_provider()

work_items_common_jira = dict(
    work_item_type=JiraWorkItemType.epic.value,
    description='Foo',
    is_bug=False,
    is_epic=True,
    tags=['acre'],
    source_last_updated=datetime.utcnow(),
    source_created_at=datetime.utcnow(),
    source_state='open'
)


def new_work_items_jira():
    return [
        dict(
            name=f'Issue {i}',
            source_id=str(i),
            source_display_id=str(i),
            url=f'http://foo.com/{i}',
            **work_items_common_jira
        )
        for i in range(100, 110)
    ]


class TestWorkItemsTopicSubscriber:
    class TestImportWorkItem:

        def it_returns_a_valid_response_when_there_are_new_work_items(self, jira_work_item_source_fixture, cleanup):
            work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture
            new_work_item = new_work_items_jira()[0]
            with patch(
                    'polaris.work_tracking.integrations.atlassian.jira_work_items_source.JiraProject.fetch_work_item') as fetch_work_item:
                fetch_work_item.return_value = new_work_item

                import_work_item_message = fake_send(
                    ImportWorkItem(send=dict(
                        organization_key=polaris_organization_key,
                        work_items_source_key=work_items_source.key,
                        source_id=new_work_item['source_display_id']
                    ))
                )

                publisher = mock_publisher()
                subscriber = WorkItemsTopicSubscriber(mock_channel, publisher=publisher)
                subscriber.consumer_context = mock_consumer

                created, updated = subscriber.dispatch(mock_channel, import_work_item_message)
                assert len(created) == 1
                publisher.assert_topic_called_with_message(WorkItemsTopic, WorkItemsCreated)

        def it_raises_an_exception_if_fetch_fails(self, jira_work_item_source_fixture, cleanup):
            work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture
            new_work_item = new_work_items_jira()[0]
            with patch(
                    'polaris.work_tracking.integrations.atlassian.jira_work_items_source.JiraProject.fetch_work_item') as fetch_work_item:
                fetch_work_item.return_value = None

                import_work_item_message = fake_send(
                    ImportWorkItem(send=dict(
                        organization_key=polaris_organization_key,
                        work_items_source_key=work_items_source.key,
                        source_id=new_work_item['source_display_id']
                    ))
                )

                publisher = mock_publisher()
                subscriber = WorkItemsTopicSubscriber(mock_channel, publisher=publisher)
                subscriber.consumer_context = mock_consumer

                with pytest.raises(ProcessingException):
                    subscriber.dispatch(mock_channel, import_work_item_message)



        def it_returns_a_valid_response_when_there_are_updated_work_items(self, jira_work_item_source_fixture, cleanup):
            work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture
            new_work_item = new_work_items_jira()[0]
            with patch(
                    'polaris.work_tracking.integrations.atlassian.jira_work_items_source.JiraProject.fetch_work_item') as fetch_work_item:
                fetch_work_item.return_value = new_work_item

                import_work_item_message = fake_send(
                    ImportWorkItem(send=dict(
                        organization_key=polaris_organization_key,
                        work_items_source_key=work_items_source.key,
                        source_id=new_work_item['source_display_id']
                    ))
                )
                # dispatch once
                publisher = mock_publisher()
                subscriber = WorkItemsTopicSubscriber(mock_channel, publisher=publisher)
                subscriber.consumer_context = mock_consumer
                subscriber.dispatch(mock_channel, import_work_item_message)
                # dispatch again
                publisher = mock_publisher()
                subscriber = WorkItemsTopicSubscriber(mock_channel, publisher=publisher)
                subscriber.consumer_context = mock_consumer
                created, updated = subscriber.dispatch(mock_channel, import_work_item_message)

                assert len(updated) == 1
                publisher.assert_topic_called_with_message(WorkItemsTopic, WorkItemsUpdated)
