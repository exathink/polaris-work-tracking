# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar


from unittest.mock import patch
import json
import pkg_resources
import pytest
import logging

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
            assert updated_state[0]['display_id'] == work_item_list[0]['source_display_id']
            assert updated_state[0]['name'] == 'Updated name'
            assert not updated_state[0]['is_new']
            assert updated_state[0]['is_updated']

            assert db.connection().execute(
                f"select name from work_tracking.work_items where source_display_id = '{work_item_list[0]['source_display_id']}'").scalar() == 'Updated name'

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

        def it_sets_is_updated_flag_to_mark_things_that_have_actual_updates(self, setup):
            fixture = setup
            project = fixture.project
            work_items_source = fixture.work_items_source
            issue_templates = fixture.issue_templates

            # fetch one issue and insert it
            work_item_list = [
                project.map_issue_to_work_item_data(issue_template)
                for issue_template in issue_templates
            ]

            initial_state = api.sync_work_items(work_items_source.key, work_item_list)
            # update one item, leave the others unchanged and process them all.
            work_item_list[0]['name'] = 'Updated name'

            # now fetch all issues and update them: so one old two new in the list
            next_state = api.sync_work_items(work_items_source.key, work_item_list)

            assert len(next_state) == 3
            assert len([result for result in next_state if result['is_new']]) == 0
            assert len([result for result in next_state if result['is_updated']]) == 1

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

                # check that the right number of results have been returned
                assert len(initial_state) == 2
                assert all([item['is_new'] for item in initial_state])
                # check that the right parent key is being returned.
                with db.orm_session() as session:
                    parent_work_item = WorkItem.find_by_source_display_id(session,
                                                                          work_items_source_id=work_items_source.id,
                                                                          source_display_id=parent_issue[
                                                                              'source_display_id'])
                    updated_child = find(initial_state,
                                         lambda item: item['display_id'] == child_issue['source_display_id'])
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
                    parent_work_item = WorkItem.find_by_source_display_id(session,
                                                                          work_items_source_id=work_items_source.id,
                                                                          source_display_id=parent_issue[
                                                                              'source_display_id'])
                    assert updated_child['parent_key'] == str(parent_work_item.key)
                    assert updated_child['is_new']

                assert db.connection().execute(
                    f"select parent_id from work_tracking.work_items where source_display_id='{child_issue['source_display_id']}'").scalar() is not None

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

                updated_child = find(next_state,
                                     lambda item: item['display_id'] == child_issue['source_display_id'])
                assert not updated_child['is_new']
                assert updated_child['is_updated']

                updated_parent = find(next_state,
                                      lambda item: item['display_id'] == parent_issue['source_display_id'])

                assert updated_parent['is_new']

                # check that the right parent key is being returned.
                with db.orm_session() as session:
                    parent_work_item = WorkItem.find_by_source_display_id(session,
                                                                          work_items_source_id=work_items_source.id,
                                                                          source_display_id=parent_issue[
                                                                              'source_display_id'])

                    assert updated_child['parent_key'] == str(parent_work_item.key)

            def it_resolves_the_parent_child_relationships_when_all_arrive_together(self, setup):
                fixture = setup
                project = fixture.project
                work_items_source = fixture.work_items_source
                issue_a = project.map_issue_to_work_item_data(fixture.issue_with_components)
                child_issue = project.map_issue_to_work_item_data(fixture.issue_with_custom_parent)
                issue_b = project.map_issue_to_work_item_data(fixture.issue_for_custom_parent)

                # original set up is:
                # issue_a -> child_issue
                # issue_a -> issue_b
                child_issue['parent_source_display_id'] = issue_a['source_display_id']
                issue_b['parent_source_display_id'] = issue_a['source_display_id']

                initial_state = api.sync_work_items(work_items_source.key, [issue_a, issue_b, child_issue])

                # check that all the relationships are set up properly.

                with db.orm_session() as session:
                    item_a = WorkItem.find_by_source_display_id(session,
                                                                work_items_source_id=work_items_source.id,
                                                                source_display_id=issue_a[
                                                                    'source_display_id'])
                    item_b = WorkItem.find_by_source_display_id(session,
                                                                work_items_source_id=work_items_source.id,
                                                                source_display_id=issue_b[
                                                                    'source_display_id'])
                    child_item = WorkItem.find_by_source_display_id(session,
                                                                    work_items_source_id=work_items_source.id,
                                                                    source_display_id=child_issue[
                                                                        'source_display_id'])

                    assert item_b.parent == item_a
                    assert child_item.parent == item_a

                    assert find(initial_state,
                                lambda item: item['display_id'] == issue_a['source_display_id'])['parent_key'] is None
                    assert find(initial_state,
                                lambda item: item['display_id'] == issue_b['source_display_id'])['parent_key'] == str(
                        item_a.key)

                    assert find(initial_state,
                                lambda item: item['display_id'] == child_issue['source_display_id'])[
                               'parent_key'] == str(item_a.key)

            def it_resolves_the_parent_child_relationships_when_all_are_existing_and_rewired(self, setup):
                fixture = setup
                project = fixture.project
                work_items_source = fixture.work_items_source
                issue_a = project.map_issue_to_work_item_data(fixture.issue_with_components)
                child_issue = project.map_issue_to_work_item_data(fixture.issue_with_custom_parent)
                issue_b = project.map_issue_to_work_item_data(fixture.issue_for_custom_parent)

                # This is the same setup as the previous test
                # we insert all three and create an existing hierarchy.

                # issue_a -> child_issue
                # issue_a -> issue_b
                child_issue['parent_source_display_id'] = issue_a['source_display_id']
                issue_b['parent_source_display_id'] = issue_a['source_display_id']

                initial_state = api.sync_work_items(work_items_source.key, [issue_a, issue_b, child_issue])

                # now we wire the relationship and sync again: child_issue becomes a child of issue_b instead of issue_a
                # issue_a -> issue_b -> child_issue

                issue_b['parent_source_display_id'] = issue_a['source_display_id']
                child_issue['parent_source_display_id'] = issue_b['source_display_id']

                next_state = api.sync_work_items(work_items_source.key, [issue_a, issue_b, child_issue])

                with db.orm_session() as session:
                    item_a = WorkItem.find_by_source_display_id(session,
                                                                work_items_source_id=work_items_source.id,
                                                                source_display_id=issue_a[
                                                                    'source_display_id'])
                    item_b = WorkItem.find_by_source_display_id(session,
                                                                work_items_source_id=work_items_source.id,
                                                                source_display_id=issue_b[
                                                                    'source_display_id'])
                    child_item = WorkItem.find_by_source_display_id(session,
                                                                    work_items_source_id=work_items_source.id,
                                                                    source_display_id=child_issue[
                                                                        'source_display_id'])

                    assert item_b.parent == item_a
                    assert child_item.parent == item_b

                    assert find(next_state,
                                lambda item: item['display_id'] == issue_a['source_display_id'])['parent_key'] is None
                    assert find(next_state,
                                lambda item: item['display_id'] == issue_b['source_display_id'])['parent_key'] == str(
                        item_a.key)

                    assert find(next_state,
                                lambda item: item['display_id'] == child_issue['source_display_id'])[
                               'parent_key'] == str(item_b.key)

        class TestParentChildResolutionAcrossWorkItemsSources:

            @pytest.fixture
            def setup(self, setup):
                fixture = setup
                cross_project_source_id = "10002"
                cross_project_wis = work_tracking.WorkItemsSource(
                    key=uuid.uuid4(),
                    connector_key=str(fixture.connector_key),
                    integration_type='jira',
                    work_items_source_type=JiraWorkItemSourceType.project.value,
                    name='test',
                    source_id=cross_project_source_id,
                    parameters=dict(),
                    account_key=account_key,
                    organization_key=organization_key,
                    commit_mapping_scope='organization',
                    import_state=WorkItemsSourceImportState.auto_update.value,
                    custom_fields=[{"id": "customfield_10014", "key": "customfield_10014", "name": "Epic Link"}]
                )

                with db.orm_session() as session:
                    session.add(cross_project_wis)
                    cross_project = JiraProject(cross_project_wis)

                yield Fixture(
                    parent=fixture,
                    cross_project_wis=cross_project_wis,
                    cross_project=cross_project
                )

            def it_syncs_parents_cross_project_when_parent_arrives_before_child(self, setup):
                fixture = setup
                project = fixture.project
                work_items_source = fixture.work_items_source
                child_issue = project.map_issue_to_work_item_data(fixture.issue_with_custom_parent)

                # create parent issue in a separate project
                cross_project = fixture.cross_project
                cross_project_wis = fixture.cross_project_wis
                parent_issue = cross_project.map_issue_to_work_item_data(fixture.issue_for_custom_parent)

                # make the parent child relationship. in the sample data these are not related by default.
                child_issue['parent_source_display_id'] = parent_issue['source_display_id']

                # first add the parent
                parent_state = api.sync_work_items(cross_project_wis.key, [parent_issue])

                child_state = api.sync_work_items(work_items_source.key, [child_issue])

                assert db.connection().execute(
                    f"select parent_id from work_tracking.work_items where source_display_id='{child_issue['source_display_id']}'").scalar() is not None

                with db.orm_session() as session:
                    parent_work_item = WorkItem.find_by_source_display_id(session,
                                                                          work_items_source_id=cross_project_wis.id,
                                                                          source_display_id=parent_issue[
                                                                              'source_display_id'])
                    updated_child = find(child_state,
                                         lambda item: item['display_id'] == child_issue['source_display_id'])
                    assert updated_child['parent_key'] == str(parent_work_item.key)
                    assert updated_child['work_items_source_key'] == str(work_items_source.key)

            def it_syncs_parents_cross_project_when_child_arrives_before_parent(self, setup):
                fixture = setup
                project = fixture.project
                work_items_source = fixture.work_items_source
                child_issue = project.map_issue_to_work_item_data(fixture.issue_with_custom_parent)

                # create parent issue in a separate project
                cross_project = fixture.cross_project
                cross_project_wis = fixture.cross_project_wis
                parent_issue = cross_project.map_issue_to_work_item_data(fixture.issue_for_custom_parent)

                # make the parent child relationship. in the sample data these are not related by default.
                child_issue['parent_source_display_id'] = parent_issue['source_display_id']

                # first add the child
                child_state = api.sync_work_items(work_items_source.key, [child_issue])
                # we cannot resolve the parent here since it has not arrived yet
                assert db.connection().execute(
                    f"select parent_id from work_tracking.work_items where source_display_id='{child_issue['source_display_id']}'").scalar() is None

                #  add the parent
                parent_state = api.sync_work_items(cross_project_wis.key, [parent_issue])

                assert db.connection().execute(
                    f"select parent_id from work_tracking.work_items where source_display_id='{child_issue['source_display_id']}'").scalar() is not None

                # we expect the parent of the child issue to be resolved and returned here.
                assert len(parent_state) == 2

                with db.orm_session() as session:
                    parent_work_item = WorkItem.find_by_source_display_id(session,
                                                                          work_items_source_id=cross_project_wis.id,
                                                                          source_display_id=parent_issue[
                                                                              'source_display_id'])
                    updated_child = find(parent_state,
                                         lambda item: item['display_id'] == child_issue['source_display_id'])
                    assert updated_child['parent_key'] == str(parent_work_item.key)
                    assert updated_child['work_items_source_key'] == str(work_items_source.key)

        class TestChangelogUpdates:

            def it_sets_the_changelog_to_null_when_it_is_not_present(self, setup):
                fixture = setup
                project = fixture.project
                work_items_source = fixture.work_items_source
                issue_templates = fixture.issue_templates

                test_issue = fixture.issue_with_components

                work_item_list = [
                    project.map_issue_to_work_item_data(test_issue)
                ]

                initial_state = api.sync_work_items(work_items_source.key, work_item_list)
                assert len(initial_state) == 1
                assert initial_state[0]['changelog'] is None

            def it_sets_the_changelog_when_it_is_provided_on_initial_import(self, setup):
                fixture = setup
                project = fixture.project
                work_items_source = fixture.work_items_source
                issue_templates = fixture.issue_templates

                test_issue = fixture.issue_with_components
                test_issue['changelog'] = {
                    "total": 1,
                    "startAt": 0,
                    "histories": [
                        {
                            "id": "17409",
                            "items": [
                                {
                                    "to": "10000",
                                    "from": None,
                                    "field": "resolution",
                                    "fieldId": "resolution",
                                    "toString": "Done",
                                    "fieldtype": "jira",
                                    "fromString": None
                                },
                                {
                                    "to": "10003",
                                    "from": "3",
                                    "field": "status",
                                    "fieldId": "status",
                                    "toString": "Done",
                                    "fieldtype": "jira",
                                    "fromString": "In Progress"
                                }
                            ],
                            "author": {
                                "self": "https://exathinkdev.atlassian.net/rest/api/2/user?accountId=557058%3Afe3847a4-f489-452f-8a83-0629c51e0455",
                                "active": True,
                                "timeZone": "America/Chicago",
                                "accountId": "557058:fe3847a4-f489-452f-8a83-0629c51e0455",
                                "avatarUrls": {
                                    "16x16": "https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png",
                                    "24x24": "https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png",
                                    "32x32": "https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png",
                                    "48x48": "https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png"
                                },
                                "accountType": "atlassian",
                                "displayName": "KrishnaK"
                            },
                            "created": "2024-02-23T08:06:38.425-0600"
                        },

                    ],
                    "maxResults": 1
                }

                work_item_list = [
                    project.map_issue_to_work_item_data(test_issue)
                ]

                initial_state = api.sync_work_items(work_items_source.key, work_item_list)

                assert len(initial_state) == 1
                assert initial_state[0]['changelog'] is not None

            def it_does_not_update_the_changelog_after_initial_import(self, setup):
                # We are enforcing this condition, since we want to maintain our own
                # state tracking after initial import. The full changelog is not sent over on
                # callbacks, and since we use the same import/update paths for both it
                # resets the OG changelog. The reason we are importing changelog is to capture the
                # OG history of changes we have not seen prior to import. The current changelog
                # is on the api_payload, so if we ever need to resync we can  create an explicit API
                # operation to do this. Trying to keep two version of the changelog in sync dynamically
                # is not worth the effort at present. We can revisit if a use case presents itself.

                fixture = setup
                project = fixture.project
                work_items_source = fixture.work_items_source
                issue_templates = fixture.issue_templates

                test_issue = fixture.issue_with_components
                test_issue['changelog'] = {
                    "total": 1,
                    "startAt": 0,
                    "histories": [
                        {
                            "id": "17409",
                            "items": [
                                {
                                    "to": "10000",
                                    "from": None,
                                    "field": "resolution",
                                    "fieldId": "resolution",
                                    "toString": "Done",
                                    "fieldtype": "jira",
                                    "fromString": None
                                },
                                {
                                    "to": "10003",
                                    "from": "3",
                                    "field": "status",
                                    "fieldId": "status",
                                    "toString": "Done",
                                    "fieldtype": "jira",
                                    "fromString": "In Progress"
                                }
                            ],
                            "author": {
                                "self": "https://exathinkdev.atlassian.net/rest/api/2/user?accountId=557058%3Afe3847a4-f489-452f-8a83-0629c51e0455",
                                "active": True,
                                "timeZone": "America/Chicago",
                                "accountId": "557058:fe3847a4-f489-452f-8a83-0629c51e0455",
                                "avatarUrls": {
                                    "16x16": "https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png",
                                    "24x24": "https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png",
                                    "32x32": "https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png",
                                    "48x48": "https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png"
                                },
                                "accountType": "atlassian",
                                "displayName": "KrishnaK"
                            },
                            "created": "2024-02-23T08:06:38.425-0600"
                        },

                    ],
                    "maxResults": 1
                }
                work_item_list = [
                    project.map_issue_to_work_item_data(test_issue)
                ]

                initial_state = api.sync_work_items(work_items_source.key, work_item_list)

                test_issue['changelog'] = None

                work_item_list = [
                    project.map_issue_to_work_item_data(test_issue)
                ]


                next_state = api.sync_work_items(work_items_source.key, work_item_list)

                assert len(next_state) == 1
                assert next_state[0]['changelog'] is not None
