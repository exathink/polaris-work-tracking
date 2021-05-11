# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2020) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal

import pytest
from unittest.mock import patch
from polaris.utils.collections import Fixture
from polaris.work_tracking.integrations.trello.trello_connector import *
from polaris.common.enums import TrelloWorkItemType
from polaris.common import db

trello_api_card_payload = {
    "id": "5e2f09ec86810e8f06e754a5",
    "checkItemStates": None,
    "closed": False,
    "dateLastActivity": "2021-04-14T09:42:09.299Z",
    "desc": "The migration in analytics-service (work_items_source_state_map table) is not applied automatically, after package update, polaris down and polaris up. Seems it shows up if you do pg_restore.",
    "descData": {
        "emoji": {
        }
    },
    "dueReminder": None,
    "idBoard": "5e17ac9e8eae873e81247bc9",
    "idList": "5e17acac71b24608074cfa79",
    "idMembersVoted": [],
    "idShort": 19,
    "idAttachmentCover": None,
    "idLabels": [
        "1"
    ],
    "manualCoverAttachment": False,
    "name": "Latest migration not applied after polaris up",
    "pos": 131071,
    "shortLink": "x28QspUQ",
    "isTemplate": False,
    "cardRole": None,
    "dueComplete": False,
    "due": None,
    "idChecklists": [],
    "idMembers": [],
    "labels": [
        {
            "id": "1",
            "idBoard": "5e17ac9e8eae873e81247bc9",
            "name": "Bug",
            "color": "red"
        }
    ],
    "shortUrl": "https://trello.com/c/x28QspUQ",
    "start": None,
    "subscribed": False,
    "url": "https://trello.com/c/x28QspUQ/19-latest-migration-not-applied-after-polaris-up",
    "cover": {
        "idAttachment": None,
        "color": None,
        "idUploadedBackground": None,
        "size": "normal",
        "brightness": "light",
        "idPlugin": None
    }
}


class TestTrelloWorkItemSource:

    @pytest.yield_fixture
    def setup(self, setup_work_item_sources, cleanup):
        _, work_items_source = setup_work_item_sources
        trello_work_items_source = work_items_source['trello']
        trello_board = TrelloBoard(token_provider=None, work_items_source=trello_work_items_source)

        yield Fixture(
            trello_board=trello_board,
            trello_card=trello_api_card_payload
        )

    def it_maps_work_item_data_correctly(self, setup):
        fixture = setup

        project = fixture.trello_board

        mapped_data = project.map_card_to_work_item(fixture.trello_card)

        assert mapped_data

        assert mapped_data['name']
        assert mapped_data['description']
        assert mapped_data['is_bug']
        assert mapped_data['work_item_type'] == TrelloWorkItemType.bug.value
        assert len(mapped_data['tags']) == 1
        assert mapped_data['url']
        assert mapped_data['source_id']
        assert mapped_data['source_display_id']
        assert mapped_data['source_last_updated']
        assert mapped_data['source_created_at']
        assert mapped_data['source_state']
        assert not mapped_data['is_epic']
        assert mapped_data['api_payload']
        assert mapped_data['commit_identifiers']
        # explicitly assert that these are the only fields mapped. The test should fail
        # and force a change in assertions if we change the mapping
        assert len(mapped_data.keys()) == 14

    def it_maps_to_correct_work_item_type_when_label_changes(self, setup):
        fixture = setup

        project = fixture.trello_board

        issue = fixture.trello_card
        issue['idLabels'] = [
            "2"
        ]
        mapped_data = project.map_card_to_work_item(issue)

        assert mapped_data

        assert not mapped_data['is_bug']
        assert mapped_data['work_item_type'] == TrelloWorkItemType.story.value

    def it_maps_to_issue_work_item_type_for_one_with_no_matching_labels(self, setup):
        fixture = setup

        project = fixture.trello_board

        issue = fixture.trello_card
        issue['idLabels'] = []
        mapped_data = project.map_card_to_work_item(issue)

        assert mapped_data

        assert not mapped_data['is_bug']
        assert mapped_data['work_item_type'] == TrelloWorkItemType.issue.value
