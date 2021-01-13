# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2020) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal

import pytest
from polaris.utils.collections import Fixture
from polaris.work_tracking.integrations.gitlab.gitlab_connector import *
from polaris.common import db

gitlab_api_issue_payload = {
    "id": 76627566,
    "iid": 2,
    "project_id": 9576833,
    "title": "Issue enhancement in progress",
    "description": "",
    "state": "closed",
    "created_at": "2021-01-01T17:30:56.367Z",
    "updated_at": "2021-01-01T18:30:56.837Z",
    "closed_at": "2021-01-01T18:30:56.809Z",
    "closed_by": {
        "id": 1438125,
        "name": "Krishna Kumar",
        "username": "krishnaku",
        "state": "active",
        "avatar_url": "https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?s=80&d=identicon",
        "web_url": "https://gitlab.com/krishnaku"
    },
    # TODO: Assuming these are hardcoded values and not real data. Discuss.
    "labels": [
        {"title": "DEV-DONE"},
        {"title": "enhancement"}
    ],
    "milestone": "None",
    "assignees": [

    ],
    "author": {
        "id": 1438125,
        "name": "Krishna Kumar",
        "username": "krishnaku",
        "state": "active",
        "avatar_url": "https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?s=80&d=identicon",
        "web_url": "https://gitlab.com/krishnaku"
    },
    "assignee": "None",
    "user_notes_count": 0,
    "merge_requests_count": 0,
    "upvotes": 0,
    "downvotes": 0,
    "due_date": "None",
    "confidential": False,
    "discussion_locked": "None",
    "web_url": "https://gitlab.com/polaris-test/test-repo/-/issues/2",
    "time_stats": {
        "time_estimate": 0,
        "total_time_spent": 0,
        "human_time_estimate": "None",
        "human_total_time_spent": "None"
    },
    "task_completion_status": {
        "count": 0,
        "completed_count": 0
    },
    "blocking_issues_count": 0,
    "has_tasks": False,
    "_links": {
        "self": "https://gitlab.com/api/v4/projects/9576833/issues/2",
        "notes": "https://gitlab.com/api/v4/projects/9576833/issues/2/notes",
        "award_emoji": "https://gitlab.com/api/v4/projects/9576833/issues/2/award_emoji",
        "project": "https://gitlab.com/api/v4/projects/9576833"
    },
    "references": {
        "short": "#2",
        "relative": "#2",
        "full": "polaris-test/test-repo#2"
    },
    "moved_to_id": "None",
    "service_desk_reply_to": "None"
}


class TestGitlabWorkItemSource:

    @pytest.yield_fixture
    def setup(self, setup_work_item_sources, cleanup):
        _, work_items_source = setup_work_item_sources
        gitlab_work_items_source = work_items_source['gitlab']
        gitlab_project = GitlabProject(token_provider=None, work_items_source=gitlab_work_items_source)

        yield Fixture(
            gitlab_project=gitlab_project,
            gitlab_issue=gitlab_api_issue_payload
        )

    def it_maps_work_item_data_correctly(self, setup):
        fixture = setup

        project = fixture.gitlab_project

        mapped_data = project.map_issue_to_work_item(fixture.gitlab_issue)

        assert mapped_data

        assert mapped_data['name']
        assert not mapped_data['description']
        assert not mapped_data['is_bug']
        assert mapped_data['work_item_type'] == 'issue'
        assert len(mapped_data['tags']) == 2
        assert mapped_data['url']
        assert mapped_data['source_id']
        assert mapped_data['source_display_id']
        assert mapped_data['source_last_updated']
        assert mapped_data['source_created_at']
        assert mapped_data['source_state']
        assert not mapped_data['is_epic']
        assert mapped_data['api_payload']
        # explicitly assert that these are the only fields mapped. The test should fail
        # and force a change in assertions if we change the mapping
        assert len(mapped_data.keys()) == 13
