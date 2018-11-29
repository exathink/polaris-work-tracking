# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import pytest
import json
import uuid
from test.constants import *
from polaris.work_tracking import message_listener
from polaris.messaging.messages import CommitsCreated, CommitWorkItemsResolved, WorkItemsCommitsResolved
from polaris.messaging.utils import pack_message, unpack_message
from unittest.mock import patch
from collections import namedtuple
from datetime import datetime

method_shim = namedtuple('method_shim', 'routing_key')

# fixtures for fields in the input message that are not used by the
    # this consumer. We still need to pass in all the fields for tests since that
    # is the message contract

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

message = CommitsCreated(send=payload).message_body

class TestCommitsCreatedMessage:

    class TestCommitWorkItemsResolved:
        def it_returns_a_valid_response(self, setup_work_items):
            with patch('polaris.messaging.topics.Topic.publish'):
                response_messages = message_listener.commits_topic_dispatch(None, method_shim(routing_key=CommitsCreated.message_type), None, message)
                assert len(response_messages) == 2
                assert response_messages[0].message_type == CommitWorkItemsResolved.message_type
                assert CommitWorkItemsResolved(receive=response_messages[0].message_body).dict
                assert response_messages[1].message_type == WorkItemsCommitsResolved.message_type
                assert WorkItemsCommitsResolved(receive=response_messages[1].message_body).dict

        def it_publishes_the_response_correctly(self, setup_work_items):
            with patch('polaris.messaging.topics.CommitsTopic.publish') as commits_topic_publish:
                with patch('polaris.messaging.topics.WorkItemsTopic.publish') as work_items_topic_publish:
                    response = message_listener.commits_topic_dispatch(None, method_shim(routing_key=CommitsCreated.message_type), None, message)
                    commits_topic_publish.assert_called_with(
                        message=response[0]
                    )
                    work_items_topic_publish.assert_called_with(
                        message=response[1]
                    )

        def it_returns_the_correct_work_item_mapping(self, setup_work_items):
            with patch('polaris.messaging.topics.Topic.publish'):
                response, _ = message_listener.commits_topic_dispatch(None, method_shim(routing_key=CommitsCreated.message_type), None, message)
                response_message = CommitWorkItemsResolved(receive=response.message_body).dict
                commit_work_items = response_message['commit_work_items']
                assert len(commit_work_items) == 2
                assert {'1002', '1003'} == {
                    work_item['display_id']

                    for entry in commit_work_items
                    for work_item in entry['work_items']
                    if entry['commit_key'] == 'A'
                }

                assert {'1005'} == {
                    work_item['display_id']

                    for entry in commit_work_items
                    for work_item in entry['work_items']
                    if entry['commit_key'] == 'B'
                }
