# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest
from pika.channel import Channel

from polaris.messaging.message_consumer import MessageConsumer
from polaris.messaging.messages import \
    ImportWorkItems, WorkItemsCreated, WorkItemsUpdated, CommitsCreated

from polaris.utils.token_provider import get_token_provider
from polaris.work_tracking.message_listener import WorkItemsTopicSubscriber
from test.constants import *

from polaris.messaging.test_utils import assert_is_valid_message

mock_channel = MagicMock(Channel)


# ----------------------------------------
# TestCommitsCreated
# -----------------------------------------

@pytest.yield_fixture()
def commit_created_message(setup_work_items):
    commit_header_ignored_fields = dict(
        commit_date=datetime.utcnow(),
        commit_date_tz_offset=0,
        committer_contributor_key=uuid.uuid4().hex,
        committer_contributor_name='Joe Blow',
        author_date=datetime.utcnow(),
        author_date_tz_offset=0,
        author_contributor_key=uuid.uuid4().hex,
        author_contributor_name='Billy Bob',
        stats=dict(
            files=10,
            insertions=2,
            deletions=9,
            lines=11
        ),
        parents=['0000', '1111'],
        created_at=datetime.utcnow(),
    )
    payload = dict(
        organization_key=rails_organization_key.hex,
        repository_name='rails',
        branch='master',
        new_commits=[
            dict(
                commit_key='A',
                commit_message='Made a change. Fixes issue #1002 and #1003',
                **commit_header_ignored_fields
            ),
            dict(
                commit_key='B',
                commit_message='Made another change. Fixes issue #1005',
                **commit_header_ignored_fields
            )
        ]
    )

    yield CommitsCreated(send=payload)


@pytest.yield_fixture()
def commit_created_no_work_items_to_resolve_message(setup_work_items):
    commit_header_ignored_fields = dict(
        commit_date=datetime.utcnow(),
        commit_date_tz_offset=0,
        committer_contributor_key=uuid.uuid4().hex,
        committer_contributor_name='Joe Blow',
        author_date=datetime.utcnow(),
        author_date_tz_offset=0,
        author_contributor_key=uuid.uuid4().hex,
        author_contributor_name='Billy Bob',
        stats=dict(
            files=10,
            insertions=2,
            deletions=9,
            lines=11
        ),
        parents=['0000', '1111'],
        created_at=datetime.utcnow(),

    )
    payload = dict(
        organization_key=rails_organization_key.hex,
        repository_name='rails',
        branch='master',
        new_commits=[
            dict(
                commit_key='A',
                commit_message='Made a change',
                **commit_header_ignored_fields
            ),
            dict(
                commit_key='B',
                commit_message='Made another change',
                **commit_header_ignored_fields
            )
        ]
    )

    yield CommitsCreated(send=payload)


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
                with patch('polaris.messaging.topics.WorkItemsTopic.publish') as work_item_topic_publish:
                    import_work_items_message = ImportWorkItems(send=dict(
                        organization_key=polaris_organization_key,
                        work_items_source_key=empty_source.key
                    ))
                    subscriber = WorkItemsTopicSubscriber(mock_channel)
                    subscriber.consumer_context = mock_consumer

                    messages = subscriber.dispatch(mock_channel, import_work_items_message)
                    assert len(messages) == 1
                    assert_is_valid_message(WorkItemsCreated, messages[0])


        def it_publishes_responses_when_there_are_new_work_items(self, setup_work_items, new_work_items):
            _, work_items_sources = setup_work_items
            empty_source = work_items_sources['empty']
            with patch(
                    'polaris.work_tracking.integrations.pivotal_tracker.PivotalTrackerProject.fetch_work_items_to_sync') as fetch_work_items_to_sync:
                fetch_work_items_to_sync.return_value = [new_work_items]
                with patch('polaris.messaging.topics.WorkItemsTopic.publish') as work_item_topic_publish:
                    import_work_items_message = ImportWorkItems(send=dict(
                        organization_key=polaris_organization_key,
                        work_items_source_key=empty_source.key
                    ))
                    subscriber = WorkItemsTopicSubscriber(mock_channel)
                    subscriber.consumer_context = mock_consumer

                    messages = subscriber.dispatch(mock_channel, import_work_items_message)
                    work_item_topic_publish.assert_any_call(messages[0])

        def it_returns_a_valid_response_when_there_are_updated_work_items(self, setup_work_items, new_work_items):
            _, work_items_sources = setup_work_items
            empty_source = work_items_sources['empty']
            with patch(
                    'polaris.work_tracking.integrations.pivotal_tracker.PivotalTrackerProject.fetch_work_items_to_sync') as fetch_work_items_to_sync:
                fetch_work_items_to_sync.return_value = [new_work_items]
                with patch('polaris.messaging.topics.WorkItemsTopic.publish') as work_item_topic_publish:
                    import_work_items_message = ImportWorkItems(send=dict(
                        organization_key=polaris_organization_key,
                        work_items_source_key=empty_source.key
                    ))
                    subscriber = WorkItemsTopicSubscriber(mock_channel)
                    subscriber.consumer_context = mock_consumer
                    # dispatch once
                    subscriber.dispatch(mock_channel, import_work_items_message)
                    # dispatch again
                    messages = subscriber.dispatch(mock_channel, import_work_items_message)
                    assert len(messages) == 1
                    assert_is_valid_message(WorkItemsUpdated, messages[0])

        def it_publishes_a_response_when_there_are_updated_work_items(self, setup_work_items, new_work_items):
            _, work_items_sources = setup_work_items
            empty_source = work_items_sources['empty']
            with patch(
                    'polaris.work_tracking.integrations.pivotal_tracker.PivotalTrackerProject.fetch_work_items_to_sync') as fetch_work_items_to_sync:
                fetch_work_items_to_sync.return_value = [new_work_items]
                with patch('polaris.messaging.topics.WorkItemsTopic.publish') as work_item_topic_publish:
                    import_work_items_message = ImportWorkItems(send=dict(
                        organization_key=polaris_organization_key,
                        work_items_source_key=empty_source.key
                    ))
                    subscriber = WorkItemsTopicSubscriber(mock_channel)
                    subscriber.consumer_context = mock_consumer
                    # dispatch once
                    subscriber.dispatch(mock_channel, import_work_items_message)
                    # dispatch again
                    messages = subscriber.dispatch(mock_channel, import_work_items_message)
                    work_item_topic_publish.assert_called_with(messages[0])

        def it_returns_a_valid_response_when_there_are_no_work_items(self, setup_work_items, new_work_items):
            _, work_items_sources = setup_work_items
            empty_source = work_items_sources['empty']
            with patch(
                    'polaris.work_tracking.integrations.pivotal_tracker.PivotalTrackerProject.fetch_work_items_to_sync') as fetch_work_items_to_sync:
                fetch_work_items_to_sync.return_value = []
                with patch('polaris.messaging.topics.WorkItemsTopic.publish') as work_item_topic_publish:
                    import_work_items_message = ImportWorkItems(send=dict(
                        organization_key=polaris_organization_key,
                        work_items_source_key=empty_source.key
                    ))
                    subscriber = WorkItemsTopicSubscriber(mock_channel)
                    subscriber.consumer_context = mock_consumer

                    messages = subscriber.dispatch(mock_channel, import_work_items_message)
                    assert len(messages) == 0

        def it_does_not_publish_a_response_when_there_are_no_work_items(self, setup_work_items, new_work_items):
            _, work_items_sources = setup_work_items
            empty_source = work_items_sources['empty']
            with patch(
                    'polaris.work_tracking.integrations.pivotal_tracker.PivotalTrackerProject.fetch_work_items_to_sync') as fetch_work_items_to_sync:
                fetch_work_items_to_sync.return_value = []
                with patch('polaris.messaging.topics.WorkItemsTopic.publish') as work_item_topic_publish:
                    import_work_items_message = ImportWorkItems(send=dict(
                        organization_key=polaris_organization_key,
                        work_items_source_key=empty_source.key
                    ))
                    subscriber = WorkItemsTopicSubscriber(mock_channel)
                    subscriber.consumer_context = mock_consumer

                    subscriber.dispatch(mock_channel, import_work_items_message)
                    assert work_item_topic_publish.call_count == 0
