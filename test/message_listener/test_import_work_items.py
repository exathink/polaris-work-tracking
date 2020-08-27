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
    ImportWorkItems, WorkItemsCreated, WorkItemsUpdated
from polaris.messaging.test_utils import mock_publisher, mock_channel, assert_topic_and_message, fake_send
from polaris.utils.token_provider import get_token_provider
from polaris.work_tracking.message_listener import WorkItemsTopicSubscriber
from polaris.messaging.topics import WorkItemsTopic
from test.constants import *

mock_channel = MagicMock(Channel)
mock_consumer = MagicMock(MessageConsumer)
mock_consumer.token_provider = get_token_provider()


class TestWorkItemsTopicSubscriber:
    class TestImportWorkItems:

        def it_returns_a_valid_response_when_there_are_new_work_items(self, setup_work_items, new_work_items):
            _, work_items_sources = setup_work_items
            empty_source = work_items_sources['empty']
            with patch(
                    'polaris.work_tracking.integrations.pivotal_tracker.PivotalTrackerProject.fetch_work_items_to_sync') as fetch_work_items_to_sync:
                fetch_work_items_to_sync.return_value = [new_work_items]

                import_work_items_message = fake_send(
                    ImportWorkItems(send=dict(
                        organization_key=polaris_organization_key,
                        work_items_source_key=empty_source.key
                    ))
                )

                publisher = mock_publisher()
                subscriber = WorkItemsTopicSubscriber(mock_channel, publisher=publisher)
                subscriber.consumer_context = mock_consumer

                messages = subscriber.dispatch(mock_channel, import_work_items_message)
                assert len(messages) == 1
                publisher.assert_topic_called_with_message(WorkItemsTopic, WorkItemsCreated)

        def it_returns_a_valid_response_when_there_are_updated_work_items(self, setup_work_items, new_work_items):
            _, work_items_sources = setup_work_items
            empty_source = work_items_sources['empty']
            with patch(
                    'polaris.work_tracking.integrations.pivotal_tracker.PivotalTrackerProject.fetch_work_items_to_sync') as fetch_work_items_to_sync:
                fetch_work_items_to_sync.return_value = [new_work_items]

                import_work_items_message = fake_send(
                    ImportWorkItems(
                        send=dict(
                            organization_key=polaris_organization_key,
                            work_items_source_key=empty_source.key
                        )
                    )
                )
                # dispatch once
                publisher = mock_publisher()
                subscriber = WorkItemsTopicSubscriber(mock_channel, publisher=publisher)
                subscriber.consumer_context = mock_consumer
                subscriber.dispatch(mock_channel, import_work_items_message)
                # dispatch again
                publisher = mock_publisher()
                subscriber = WorkItemsTopicSubscriber(mock_channel, publisher=publisher)
                subscriber.consumer_context = mock_consumer
                messages = subscriber.dispatch(mock_channel, import_work_items_message)

                assert len(messages) == 1
                publisher.assert_topic_called_with_message(WorkItemsTopic, WorkItemsUpdated)

        def it_does_not_publish_a_response_when_there_are_no_work_items(self, setup_work_items, new_work_items):
            _, work_items_sources = setup_work_items
            empty_source = work_items_sources['empty']
            with patch(
                    'polaris.work_tracking.integrations.pivotal_tracker.PivotalTrackerProject.fetch_work_items_to_sync') as fetch_work_items_to_sync:
                fetch_work_items_to_sync.return_value = []

                import_work_items_message = fake_send(
                    ImportWorkItems(
                        send=dict(
                            organization_key=polaris_organization_key,
                            work_items_source_key=empty_source.key
                        )
                    )
                )
                publisher = mock_publisher()
                subscriber = WorkItemsTopicSubscriber(mock_channel, publisher=publisher)
                subscriber.consumer_context = mock_consumer

                subscriber.dispatch(mock_channel, import_work_items_message)
                publisher.assert_not_called()
