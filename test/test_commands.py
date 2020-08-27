# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar


from unittest.mock import patch

from polaris.utils.token_provider import get_token_provider

from polaris.work_tracking import commands
from polaris.utils.collections import object_to_dict
from .fixtures.jira_fixtures import *

token_provider = get_token_provider()


class TestPivotalSyncWorkItems:

    def it_imports_work_items_when_the_source_has_no_work_items(self, setup_work_items, new_work_items):
        _, work_items_sources = setup_work_items
        empty_source = work_items_sources['empty']
        with patch(
                'polaris.work_tracking.integrations.pivotal_tracker.PivotalTrackerProject.fetch_work_items_to_sync') as fetch_work_items_to_sync:
            fetch_work_items_to_sync.return_value = [new_work_items]

            for result in commands.sync_work_items(token_provider, empty_source.key):
                assert len(result) == len(new_work_items)
                assert all(map(lambda item: item['is_new'], result))

    def it_updates_work_items_that_already_exist(self, setup_work_items, new_work_items):
        _, work_items_sources = setup_work_items
        empty_source = work_items_sources['empty']
        with patch(
                'polaris.work_tracking.integrations.pivotal_tracker.PivotalTrackerProject.fetch_work_items_to_sync') as fetch_work_items_to_sync:
            fetch_work_items_to_sync.return_value = [new_work_items]
            # import once and ignore results
            for _ in commands.sync_work_items(token_provider, empty_source.key):
                pass

            # import again
            for result in commands.sync_work_items(token_provider, empty_source.key):
                assert len(result) == len(new_work_items)
                assert all(map(lambda item: not item['is_new'], result))


class TestJiraSyncWorkItemsForEpic:

    def it_imports_when_a_mapped_work_item_is_new(self, jira_work_items_fixture, new_work_items, cleanup):
        work_items, work_items_source, jira_project_id, connector_key = jira_work_items_fixture
        with patch(
                'polaris.work_tracking.integrations.atlassian.jira_work_items_source.JiraProject.fetch_work_items_for_epic') as fetch_work_items_for_epic:
            fetch_work_items_for_epic.return_value = [new_work_items]
            epic_issue = [issue for issue in work_items if issue.is_epic][0]
            epic = object_to_dict(
                epic_issue,
                ['key',
                 'name',
                 'description',
                 'work_item_type',
                 'is_bug',
                 'is_epic',
                 'tags',
                 'source_id',
                 'source_display_id',
                 'source_state',
                 'url',
                 'source_created_at',
                 'source_last_updated',
                 'last_sync',
                 'epic_id'],
                {
                    'source_display_id': 'display_id',
                    'source_created_at': 'created_at',
                    'source_last_updated': 'last_updated',
                    'source_state': 'state',
                    'epic_id': 'epic_key'}
            )

            for result in commands.sync_work_items_for_epic(work_items_source.key, epic):
                assert len(result) == len(new_work_items)
                assert all(map(lambda item: item['is_new'], result))

    def it_updates_when_a_mapped_work_item_is_existing(self, jira_work_items_fixture, new_work_items, cleanup):
        work_items, work_items_source, jira_project_id, connector_key = jira_work_items_fixture
        mapped_work_items = [
            object_to_dict(
                issue,
                ['name',
                 'description',
                 'work_item_type',
                 'is_bug',
                 'is_epic',
                 'tags',
                 'source_id',
                 'source_display_id',
                 'source_state',
                 'url',
                 'source_created_at',
                 'source_last_updated'
                 ]
            )
            for issue in work_items if not issue.is_epic
        ]
        with patch(
                'polaris.work_tracking.integrations.atlassian.jira_work_items_source.JiraProject.fetch_work_items_for_epic') as fetch_work_items_for_epic:
            fetch_work_items_for_epic.return_value = [mapped_work_items]
            epic_issue = [issue for issue in work_items if issue.is_epic][0]
            epic = object_to_dict(
                epic_issue,
                ['key',
                 'name',
                 'description',
                 'work_item_type',
                 'is_bug',
                 'is_epic',
                 'tags',
                 'source_id',
                 'source_display_id',
                 'source_state',
                 'url',
                 'source_created_at',
                 'source_last_updated',
                 'last_sync',
                 'epic_id'],
                {
                    'source_display_id': 'display_id',
                    'source_created_at': 'created_at',
                    'source_last_updated': 'last_updated',
                    'source_state': 'state',
                    'epic_id': 'epic_key'}
            )

            for result in commands.sync_work_items_for_epic(work_items_source.key, epic):
                assert len(result) == len(mapped_work_items)
                assert all(map(lambda item: not item['is_new'], result))
