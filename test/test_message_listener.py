# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from collections import namedtuple
from datetime import datetime
from unittest.mock import patch, MagicMock, Mock

import pytest
from pika.channel import Channel

from polaris.utils.token_provider import get_token_provider

from polaris.messaging.messages import \
    CommitsCreated, \
    CommitsWorkItemsResolved, \
    WorkItemsCommitsResolved, \
    WorkItemsCommitsUpdated, \
    ImportWorkItems, \
    WorkItemsCreated,\
    WorkItemsImported


from polaris.messaging.message_consumer import MessageConsumer
from polaris.work_tracking.message_listener import CommitsTopicSubscriber, WorkItemsTopicSubscriber, CommandsTopicSubscriber
from polaris.common import db
from test.constants import *
from .helpers import find_work_items

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
        author_contributor_name='Billy Bob'
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
        author_contributor_name='Billy Bob'
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

class TestCommitsTopicSubscriber:

    class TestCommitsCreatedMessage:
        def it_returns_a_valid_response(self, commit_created_message):
            with patch('polaris.messaging.topics.Topic.publish'):
                response_messages = CommitsTopicSubscriber(mock_channel).dispatch(mock_channel, commit_created_message)
                assert len(response_messages) == 2
                assert response_messages[0].message_type == CommitsWorkItemsResolved.message_type
                assert CommitsWorkItemsResolved(receive=response_messages[0].message_body).dict
                assert response_messages[1].message_type == WorkItemsCommitsResolved.message_type
                assert WorkItemsCommitsResolved(receive=response_messages[1].message_body).dict

        def it_publishes_the_response_correctly(self, commit_created_message):
            with patch('polaris.messaging.topics.CommitsTopic.publish') as commits_topic_publish:
                with patch('polaris.messaging.topics.WorkItemsTopic.publish') as work_items_topic_publish:
                    subscriber = CommitsTopicSubscriber(mock_channel)
                    response = subscriber.dispatch(mock_channel, commit_created_message)
                    commits_topic_publish.assert_called_with(
                        message=response[0]
                    )
                    work_items_topic_publish.assert_called_with(
                        message=response[1]
                    )

        def it_publishes_a_response_even_if_no_work_items_were_resolved(self, commit_created_no_work_items_to_resolve_message):
            with patch('polaris.messaging.topics.CommitsTopic.publish') as commits_topic_publish:
                with patch('polaris.messaging.topics.WorkItemsTopic.publish') as work_items_topic_publish:
                    response = CommitsTopicSubscriber(mock_channel).dispatch(mock_channel, commit_created_no_work_items_to_resolve_message)
                    commits_topic_publish.assert_called_with(
                        message=response[0]
                    )
                    work_items_topic_publish.assert_called_with(
                        message=response[1]
                    )

# ----------------------------------------
# Test WorkItemCommitsResolved
# ----------------------------------------

@pytest.yield_fixture()
def work_items_commits_resolved_message(setup_work_items):
    work_item_1000 = find_work_items(rails_work_items_source_key, ['1000'])[0]

    commit_header_common_fields = dict(
        commit_message="Made an update, here is the fix",
        commit_date=datetime.utcnow(),
        commit_date_tz_offset=0,
        committer_contributor_key=uuid.uuid4().hex,
        committer_contributor_name='Joe Blow',
        author_date=datetime.utcnow(),
        author_date_tz_offset=0,
        author_contributor_key=uuid.uuid4().hex,
        author_contributor_name='Billy Bob'
    )
    payload = dict(
        organization_key=rails_organization_key.hex,
        repository_name='rails',
        work_items_commits = [
            dict(
                work_item_key=work_item_1000.key,
                commit_headers=[
                    dict(
                        commit_key='XXXX',
                        **commit_header_common_fields
                    )
                ]
            )
        ]
    )

    yield WorkItemsCommitsResolved(send=payload)

    db.connection().execute("delete from work_tracking.work_items_commits")
    db.connection().execute("delete from work_tracking.cached_commits")


class TestWorkItemsTopicSubscriber:

    class TestWorkItemsCommitsResolved:
        def it_returns_a_valid_response(self, work_items_commits_resolved_message):
            with patch('polaris.messaging.topics.Topic.publish'):
                response_message = WorkItemsTopicSubscriber(mock_channel).dispatch(mock_channel, work_items_commits_resolved_message)
                assert response_message
                assert response_message.message_type == WorkItemsCommitsUpdated.message_type
                assert WorkItemsCommitsUpdated(receive=response_message.message_body).dict


        def it_publishes_the_response_correctly(self, work_items_commits_resolved_message):
            with patch('polaris.messaging.topics.WorkItemsTopic.publish') as work_item_topic_publish:
                response_message = WorkItemsTopicSubscriber(mock_channel).dispatch(mock_channel, work_items_commits_resolved_message)
                work_item_topic_publish.assert_called_with(message=response_message)

        def it_processes_and_publishes_the_response_even_if_there_are_no_commits_to_update(self):
            with patch('polaris.messaging.topics.WorkItemsTopic.publish') as work_item_topic_publish:
                no_work_items_message = WorkItemsCommitsResolved(
                    send=dict(
                        organization_key=rails_organization_key,
                        repository_name='rails',
                        work_items_commits=[]
                    )
                )
                response_message = WorkItemsTopicSubscriber(mock_channel).dispatch(mock_channel, no_work_items_message )
                work_item_topic_publish.assert_called_with(message=response_message)




mock_consumer = MagicMock(MessageConsumer)
mock_consumer.token_provider = get_token_provider()

class TestCommandsTopicSubscriber:

    class TestImportWorkItems:

        def it_returns_a_valid_response_when_there_are_new_work_items(self, setup_work_items, new_work_items,
                                                                    cleanup_empty):
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
                    subscriber = CommandsTopicSubscriber(mock_channel)
                    subscriber.consumer_context = mock_consumer

                    imported_message, created_message = subscriber.dispatch(mock_channel,import_work_items_message)
                    assert imported_message is not None
                    assert created_message is not None
                    assert WorkItemsImported(receive=imported_message.message_body)
                    assert WorkItemsCreated(receive=created_message.message_body)

        def it_publishes_responses_when_there_are_new_work_items(self, setup_work_items, new_work_items,
                                                                    cleanup_empty):
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
                    subscriber = CommandsTopicSubscriber(mock_channel)
                    subscriber.consumer_context = mock_consumer

                    imported_message, created_message = subscriber.dispatch(mock_channel,import_work_items_message)
                    work_item_topic_publish.assert_any_call(message=imported_message)
                    work_item_topic_publish.assert_any_call(message=created_message)


        def it_returns_a_valid_response_when_there_are_no_new_work_items(self, setup_work_items, new_work_items,
                                                                    cleanup_empty):
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
                    subscriber = CommandsTopicSubscriber(mock_channel)
                    subscriber.consumer_context = mock_consumer
                    # dispatch once
                    subscriber.dispatch(mock_channel, import_work_items_message)
                    # dispatch again
                    imported_message, created_message = subscriber.dispatch(mock_channel,import_work_items_message)
                    assert imported_message is not None
                    assert created_message is None
                    assert WorkItemsImported(receive=imported_message.message_body)

        def it_published_response_when_there_are_no_new_work_items(self, setup_work_items, new_work_items,
                                                                    cleanup_empty):
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
                    subscriber = CommandsTopicSubscriber(mock_channel)
                    subscriber.consumer_context = mock_consumer
                    # dispatch once
                    subscriber.dispatch(mock_channel, import_work_items_message)
                    # dispatch again
                    imported_message, _ = subscriber.dispatch(mock_channel,import_work_items_message)
                    work_item_topic_publish.assert_called_with(message=imported_message)

        def it_returns_a_valid_response_when_there_are_no_work_items(self, setup_work_items, new_work_items,
                                                                    cleanup_empty):
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
                    subscriber = CommandsTopicSubscriber(mock_channel)
                    subscriber.consumer_context = mock_consumer

                    imported_message, created_message = subscriber.dispatch(mock_channel,import_work_items_message)
                    assert imported_message is not None
                    assert created_message is None
                    assert WorkItemsImported(receive=imported_message.message_body)



        def it_publishes_a_response_when_there_are_no_work_items(self, setup_work_items, new_work_items,
                                                                    cleanup_empty):
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
                    subscriber = CommandsTopicSubscriber(mock_channel)
                    subscriber.consumer_context = mock_consumer

                    imported_message, _ = subscriber.dispatch(mock_channel,import_work_items_message)
                    work_item_topic_publish.assert_called_with(message=imported_message)