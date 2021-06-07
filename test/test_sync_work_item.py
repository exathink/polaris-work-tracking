# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal


from unittest.mock import patch

from polaris.utils.token_provider import get_token_provider
from polaris.work_tracking import commands
from .fixtures.jira_fixtures import *

token_provider = get_token_provider()

work_items_common = dict(
    work_item_type=JiraWorkItemType.epic.value,
    description='Foo',
    is_bug=False,
    is_epic=True,
    tags=['acre'],
    source_last_updated=datetime.utcnow(),
    source_created_at=datetime.utcnow(),
    source_state='open'
)


@pytest.fixture
def new_work_items():
    return [
        dict(
            name=f'Issue {i}',
            source_id=str(i),
            source_display_id=str(i),
            url=f'http://foo.com/{i}',
            **work_items_common
        )
        for i in range(100, 110)
    ]


class TestSyncWorkItemForJira:

    def it_assigns_work_item_key_to_new_work_item(self, jira_work_item_source_fixture, cleanup):
        work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture
        new_work_item = new_work_items()[0]
        with patch(
                'polaris.work_tracking.integrations.atlassian.jira_work_items_source.JiraProject.fetch_work_item') as fetch_work_item:
            fetch_work_item.return_value = [new_work_item]

            for result in commands.sync_work_item(token_provider, work_items_source.key,
                                                  new_work_item['source_display_id']):
                assert result['display_id'] == new_work_item['source_display_id']
                assert result['is_new'] == True
                assert result['key'] is not None

    def it_updates_work_item_that_already_exists(self, jira_work_item_source_fixture, cleanup):
        work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture
        new_work_item = new_work_items()[0]
        with patch(
                'polaris.work_tracking.integrations.atlassian.jira_work_items_source.JiraProject.fetch_work_item') as fetch_work_item:
            fetch_work_item.return_value = [new_work_item]
            # import once
            for result in commands.sync_work_item(token_provider, work_items_source.key,
                                                  new_work_item['source_display_id']):
                pass

            # import again
            for result in commands.sync_work_item(token_provider, work_items_source.key,
                                                  new_work_item['source_display_id']):
                assert result['display_id'] == new_work_item['source_display_id']
                assert result['is_updated'] == True
