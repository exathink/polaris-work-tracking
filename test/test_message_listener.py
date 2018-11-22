# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import pytest
import json

from test.constants import *
from polaris.work_tracking import message_listener
from polaris.messaging.messages import CommitWorkItemsResolved, MessageTypes
from polaris.messaging.utils import pack_message, unpack_message
from unittest.mock import patch

class TestCommitHistoryImportedMessage:
    # fixtures for fields in the input message that are not used by the
    # this consumer. We still need to pass in all the fields for tests since that
    # is the message contract

    branch_ignored_fields = dict(
        name='master',
        is_new=False,
        is_default=True,
        is_stale=False,
        remote_head='XXXXX',
        is_orphan=False
    )
    commit_summary_ignored_fields = dict(
        commit_date_raw=0,
        commit_date='',
        commit_date_tz_offset=0,
        committer_alias='',
        committer_name='',
        author_date_raw=0,
        author_date='',
        author_date_tz_offset=0,
        author_alias='',
        author_name=''
    )
    payload = json.dumps(
        dict(
            organization_key=rails_organization_key.hex,
            repository_name='rails',
            branch=branch_ignored_fields,
            commit_summaries=[
                dict(
                    commit_key='A',
                    commit_message='Made a change. Fixes issue #1002 and #1003',
                    **commit_summary_ignored_fields
                ),
                dict(
                    commit_key='B',
                    commit_message='Made another change. Fixes issue #1005',
                    **commit_summary_ignored_fields
                )
            ]
        )
    )
    message = pack_message(MessageTypes.commit_history_imported, payload)

    def it_returns_a_valid_response(self, setup_work_items):
        with patch('polaris.work_tracking.message_listener.publish'):
            response = message_listener.dispatch(self.message)
            message_type, payload = unpack_message(response)
            assert message_type == MessageTypes.commit_work_items_resolved
            assert payload
            response_message = CommitWorkItemsResolved().loads(payload)
            assert response_message

    def it_publishes_the_response_correctly(self, setup_work_items):
        with patch('polaris.work_tracking.message_listener.publish') as publish:
            response = message_listener.dispatch(self.message)
            publish.assert_called_with(
                exchange='commits',
                message=response,
                routing_key=MessageTypes.commit_work_items_resolved
            )

    def it_returns_the_correct_work_item_mapping(self, setup_work_items):
        with patch('polaris.work_tracking.message_listener.publish'):
            response = message_listener.dispatch(self.message)
            message_type, payload = unpack_message(response)
            response_message = CommitWorkItemsResolved().loads(payload)
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



