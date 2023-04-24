# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar


from unittest.mock import patch
import json
import pkg_resources
from polaris.work_tracking.integrations.atlassian.jira_work_items_source import JiraProject

from polaris.utils.token_provider import get_token_provider
from polaris.work_tracking import commands
from polaris.work_tracking.db import api
from polaris.work_tracking.db.model import WorkItem
from polaris.utils.collections import find

token_provider = get_token_provider()

from .fixtures.jira_fixtures import *


# these tests exercise the command sync logic - they dont test the actual db writes.
class TestSyncCommand:

    def it_imports_work_items_when_the_source_has_no_work_items(self, setup_work_items, new_work_items):
        _, work_items_sources = setup_work_items
        empty_source = work_items_sources['empty']
        with patch(
                'polaris.work_tracking.integrations.pivotal_tracker.PivotalTrackerProject.fetch_work_items_to_sync') as fetch_work_items_to_sync:
            fetch_work_items_to_sync.return_value = [new_work_items]

            for result in commands.sync_work_items(token_provider, empty_source.key):
                assert len(result) == len(new_work_items)
                assert all(map(lambda item: item['is_new'], result))

    def it_assigns_work_item_keys_to_new_work_items(self, setup_work_items, new_work_items):
        _, work_items_sources = setup_work_items
        empty_source = work_items_sources['empty']
        with patch(
                'polaris.work_tracking.integrations.pivotal_tracker.PivotalTrackerProject.fetch_work_items_to_sync') as fetch_work_items_to_sync:
            fetch_work_items_to_sync.return_value = [new_work_items]

            for result in commands.sync_work_items(token_provider, empty_source.key):
                assert len(result) == len(new_work_items)
                assert all(map(lambda item: item['key'] is not None, result))

    def it_updates_work_items_that_already_exist(self, setup_work_items, new_work_items):
        _, work_items_sources = setup_work_items
        empty_source = work_items_sources['empty']
        with patch(
                'polaris.work_tracking.integrations.pivotal_tracker.PivotalTrackerProject.fetch_work_items_to_sync') as fetch_work_items_to_sync:
            fetch_work_items_to_sync.return_value = [new_work_items]
            # import once
            for result in commands.sync_work_items(token_provider, empty_source.key):
                pass

            # import again
            for result in commands.sync_work_items(token_provider, empty_source.key):
                assert len(result) == len(new_work_items)
                assert all(map(lambda item: not item['is_new'], result))

    def it_generates_multiple_results_sets_if_the_input_has_multiple_batches(self, setup_work_items, new_work_items):
        _, work_items_sources = setup_work_items
        empty_source = work_items_sources['empty']
        with patch(
                'polaris.work_tracking.integrations.pivotal_tracker.PivotalTrackerProject.fetch_work_items_to_sync') as fetch_work_items_to_sync:
            fetch_work_items_to_sync.return_value = [new_work_items[0:5], new_work_items[5:10]]

            results = []
            for result in commands.sync_work_items(token_provider, empty_source.key):
                results.append(result)

            assert len(results) == 2

            for result in results:
                assert len(result) == len(new_work_items) / 2
                assert all(map(lambda item: item['is_new'], result))


# These tests exercise the low level api sync logic, including the db writes.
class TestSyncApi(WorkItemsSourceTest):
    class TestSync:
        @pytest.fixture()
        def setup(self, setup):
            fixture = setup
            work_items_source = fixture.work_items_source
            issue_templates = [
                json.loads(
                    pkg_resources.resource_string(__name__, data_file)
                )
                for data_file in [
                    './data/jira_payload_with_custom_parent.json',
                    './data/jira_payload_for_custom_parent.json',
                    './data/jira_payload_with_components.json'
                ]
            ]

            with db.orm_session() as session:
                session.add(work_items_source)
                project = JiraProject(work_items_source)

            yield Fixture(
                organization_key=organization_key,
                project=project,
                work_items_source=work_items_source,
                connector_key=work_items_source.connector_key,
                issue_templates=issue_templates,
                issue_with_custom_parent=issue_templates[0],
                issue_for_custom_parent=issue_templates[1],
                issue_with_components=issue_templates[2],
            )

        def it_inserts_a_set_of_new_work_items(self, setup):
            fixture = setup
            project = fixture.project
            work_items_source = fixture.work_items_source
            issue_templates = fixture.issue_templates

            # Fetch all issues
            work_item_list = [
                project.map_issue_to_work_item_data(issue_template)
                for issue_template in issue_templates
            ]

            sync_results = api.sync_work_items(work_items_source.key, work_item_list)
            assert len(sync_results) == 3
            assert all([result['is_new'] for result in sync_results])
            assert db.connection().execute('select count(id) from work_tracking.work_items').scalar() == 3

        def it_updates_existing_work_items(self, setup):
            fixture = setup
            project = fixture.project
            work_items_source = fixture.work_items_source
            issue_templates = fixture.issue_templates

            work_item_list = [
                project.map_issue_to_work_item_data(issue_template)
                for issue_template in issue_templates
            ]

            initial_state = api.sync_work_items(work_items_source.key, work_item_list)

            work_item_list[0]['name'] = 'Updated name'
            updated_state = api.sync_work_items(work_items_source.key, work_item_list[0:1])

            assert len(updated_state) == 1
            assert updated_state[0]['display_id'] == initial_state[0]['display_id']
            assert updated_state[0]['name'] == 'Updated name'

            assert db.connection().execute(
                f"select name from work_tracking.work_items where source_display_id = '{initial_state[0]['display_id']}'").scalar() == 'Updated name'

        def it_processes_inserts_and_updates(self, setup):
            fixture = setup
            project = fixture.project
            work_items_source = fixture.work_items_source
            issue_templates = fixture.issue_templates

            # fetch one issue and insert it
            work_item_list = [
                project.map_issue_to_work_item_data(issue_templates[0])
            ]

            initial_state = api.sync_work_items(work_items_source.key, work_item_list)

            # now fetch all issues and update them: so one old two new in the list
            next_state = api.sync_work_items(work_items_source.key, [
                project.map_issue_to_work_item_data(issue_template)
                for issue_template in issue_templates
            ])

            assert len(next_state) == 3
            assert len([result for result in next_state if result['is_new']]) == 2

            assert db.connection().execute('select count(id) from work_tracking.work_items').scalar() == 3

        class TestParentChildResolution:

            def it_resolves_the_parent_child_relationship_if_the_parent_and_child_arrive_together(self, setup):
                fixture = setup
                project = fixture.project
                work_items_source = fixture.work_items_source
                child_issue = project.map_issue_to_work_item_data(fixture.issue_with_custom_parent)
                parent_issue = project.map_issue_to_work_item_data(fixture.issue_for_custom_parent)

                # make the parent child relationship. in the sample data these are not related by default.
                child_issue['parent_source_display_id'] = parent_issue['source_display_id']

                initial_state = api.sync_work_items(work_items_source.key, [child_issue, parent_issue])

                # check that parent id has been assigned in the db.
                assert db.connection().execute(
                    f"select parent_id from work_tracking.work_items where source_display_id='{child_issue['source_display_id']}'").scalar() is not None

                #check that the right number of results have been returned
                assert len(initial_state) == 2

                # check that the right parent key is being returned.
                with db.orm_session() as session:
                    parent_work_item = WorkItem.find_by_source_display_id(session, work_items_source_id=work_items_source.id, source_display_id=parent_issue['source_display_id'])
                    updated_child = find(initial_state, lambda item: item['display_id'] == child_issue['source_display_id'])
                    assert updated_child['parent_key'] == str(parent_work_item.key)

            def it_resolves_the_parent_child_relationship_if_the_parent_arrives_before_the_child(self, setup):
                fixture = setup
                project = fixture.project
                work_items_source = fixture.work_items_source
                child_issue = project.map_issue_to_work_item_data(fixture.issue_with_custom_parent)
                parent_issue = project.map_issue_to_work_item_data(fixture.issue_for_custom_parent)

                # make the parent child relationship. in the sample data these are not related by default.
                child_issue['parent_source_display_id'] = parent_issue['source_display_id']

                initial_state = api.sync_work_items(work_items_source.key, [parent_issue])
                next_state = api.sync_work_items(work_items_source.key, [child_issue])


                assert len(next_state) == 1
                updated_child = next_state[0]

                assert updated_child['parent_key'] is not None
                with db.orm_session() as session:
                    parent_work_item = WorkItem.find_by_source_display_id(session, work_items_source_id=work_items_source.id, source_display_id=parent_issue['source_display_id'])
                    assert updated_child['parent_key'] == str(parent_work_item.key)

                assert db.connection().execute(f"select parent_id from work_tracking.work_items where source_display_id='{child_issue['source_display_id']}'").scalar() is not None


            def it_resolves_the_parent_child_relationship_if_the_child_arrives_before_the_parent(self, setup):
                fixture = setup
                project = fixture.project
                work_items_source = fixture.work_items_source
                child_issue = project.map_issue_to_work_item_data(fixture.issue_with_custom_parent)
                parent_issue = project.map_issue_to_work_item_data(fixture.issue_for_custom_parent)

                # make the parent child relationship. in the sample data these are not related by default.
                child_issue['parent_source_display_id'] = parent_issue['source_display_id']
                initial_state = api.sync_work_items(work_items_source.key, [child_issue])


                next_state = api.sync_work_items(work_items_source.key, [parent_issue])
                assert db.connection().execute(
                    f"select parent_id from work_tracking.work_items where source_display_id='{child_issue['source_display_id']}'").scalar() is not None

                # we want to see the child here since it's parent id should have been updated
                # when the new parent came in.
                assert len(next_state) == 2

                # check that the right parent key is being returned.
                with db.orm_session() as session:
                    parent_work_item = WorkItem.find_by_source_display_id(session,
                                                                          work_items_source_id=work_items_source.id,
                                                                          source_display_id=parent_issue[
                                                                              'source_display_id'])
                    updated_child = find(next_state,
                                         lambda item: item['display_id'] == child_issue['source_display_id'])

                    assert updated_child['parent_key'] == str(parent_work_item.key)
                    assert not updated_child['is_new']
