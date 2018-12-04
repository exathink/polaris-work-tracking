# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar
import pytest
from datetime import datetime
from polaris.work_tracking import work_tracker
from test.constants import *
from .helpers import find_work_items
from polaris.utils.token_provider import get_token_provider
from polaris.common import db
from polaris.work_tracking.db.model import WorkItemsSource, cached_commits
from unittest.mock import patch

token_provider = get_token_provider()

class TestSyncWorkItems:


    def it_imports_work_items_when_the_source_has_no_work_items(self, setup_work_items, new_work_items,
                                                                cleanup_empty):
        _, work_items_sources = setup_work_items
        empty_source = work_items_sources['empty']
        with patch('polaris.work_tracking.integrations.pivotal_tracker.PivotalTrackerProject.fetch_work_items_to_sync') as fetch_work_items_to_sync:
            fetch_work_items_to_sync.return_value = [new_work_items]

            result = work_tracker.sync_work_items(token_provider, empty_source.key)
            assert len(result['new_work_items']) == len(new_work_items)
            assert result['created'] == len(new_work_items)
            assert result['updated'] == 0
            assert result['total'] == 10

    def it_updates_work_items_that_already_exist(self, setup_work_items, new_work_items,
                                                                cleanup_empty):
        _, work_items_sources = setup_work_items
        empty_source = work_items_sources['empty']
        with patch('polaris.work_tracking.integrations.pivotal_tracker.PivotalTrackerProject.fetch_work_items_to_sync') as fetch_work_items_to_sync:
            fetch_work_items_to_sync.return_value = [new_work_items]
            # import once
            work_tracker.sync_work_items(token_provider, empty_source.key)
            # import again
            result = work_tracker.sync_work_items(token_provider, empty_source.key)
            assert result['new_work_items'] == []
            assert result['created'] == 0
            assert result['updated'] == len(new_work_items)
            assert result['total'] == 10









# -------------------------------------------
# Resolve work items from commits
#--------------------------------------------
class TestResolveWorkItemsFromCommits:

    class ContextGithubWorkItems:

        def it_resolves_work_items_when_a_commit_message_contains_a_single_issue_reference(self, setup_work_items):
            commit_headers = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes #1000 "
                )
            ]
            resolved, _ = work_tracker.resolve_work_items_from_commit_headers(rails_organization_key, commit_headers)
            assert len(resolved) == 1
            assert resolved[0]['commit_key'] == 'A'
            assert resolved[0]['work_items'][0]['display_id'] == '1000'

        def it_resolves_work_items_when_a_commit_message_contains_a_multiple_issue_references(self, setup_work_items):
            commit_headers = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes #1000 and #1002 "
                )
            ]
            resolved, _ = work_tracker.resolve_work_items_from_commit_headers(rails_organization_key, commit_headers)
            assert len(resolved) == 1
            assert resolved[0]['commit_key'] == 'A'
            assert {'1000', '1002'} == {work_item['display_id'] for work_item in resolved[0]['work_items']}


        def it_resolves_work_items_for_multiple_commits(self, setup_work_items):
            commit_headers = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes #1000 and #1002 "
                ),
                dict(
                    commit_key='B',
                    commit_message=" Do something that fixes #1003"
                )
            ]
            resolved, _ = work_tracker.resolve_work_items_from_commit_headers(rails_organization_key, commit_headers)
            assert len(resolved) == 2

            assert {'1000', '1002'} == {
                work_item['display_id']

                for entry in resolved
                for work_item  in entry['work_items']
                if entry['commit_key'] == 'A'
            }

            assert {'1003'} == {
                work_item['display_id']

                for entry in resolved
                for work_item in entry['work_items']
                if entry['commit_key'] == 'B'
            }


        def it_omits_issue_references_where_there_is_no_matching_work_item(self, setup_work_items):
            commit_headers = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes #1000 and #5000 "
                )
            ]
            resolved, _ = work_tracker.resolve_work_items_from_commit_headers(rails_organization_key, commit_headers)
            assert len(resolved) == 1
            assert {'1000'} == {work_item['display_id'] for work_item in resolved[0]['work_items']}

        def it_omits_commits_where_there_are_no_matching_work_items(self, setup_work_items):
            commit_headers = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes #1000 and #1002 "
                ),
                dict(
                    commit_key='B',
                    commit_message=" Do something that fixes #5000"
                )
            ]
            resolved, _ = work_tracker.resolve_work_items_from_commit_headers(rails_organization_key, commit_headers)
            assert len(resolved) == 1




    class ContextPivotalWorkItems:

        def it_resolves_work_items_when_a_commit_message_contains_a_single_issue_reference(self, setup_work_items):
            commit_headers = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes [#2000 ]"
                )
            ]
            resolved, _ = work_tracker.resolve_work_items_from_commit_headers(polaris_organization_key, commit_headers)
            assert len(resolved) == 1
            assert resolved[0]['commit_key'] == 'A'
            assert resolved[0]['work_items'][0]['display_id'] == '2000'

        def it_resolves_work_items_when_a_commit_message_contains_a_multiple_issue_references(self, setup_work_items):
            commit_headers = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that [fixes #2000 and #2002] "
                )
            ]
            resolved, _ = work_tracker.resolve_work_items_from_commit_headers(polaris_organization_key, commit_headers)
            assert len(resolved) == 1
            assert resolved[0]['commit_key'] == 'A'
            assert {'2000', '2002'} == {work_item['display_id'] for work_item in resolved[0]['work_items']}


        def it_resolves_work_items_for_multiple_commits(self, setup_work_items):
            commit_headers = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes [#2000 and #2002] "
                ),
                dict(
                    commit_key='B',
                    commit_message=" Do something that [fixes #2003]"
                )
            ]
            resolved, _ = work_tracker.resolve_work_items_from_commit_headers(polaris_organization_key, commit_headers)
            assert len(resolved) == 2

            assert {'2000', '2002'} == {
                work_item['display_id']

                for entry in resolved
                for work_item  in entry['work_items']
                if entry['commit_key'] == 'A'
            }

            assert {'2003'} == {
                work_item['display_id']

                for entry in resolved
                for work_item in entry['work_items']
                if entry['commit_key'] == 'B'
            }


        def it_omits_issue_references_where_there_is_no_matching_work_item(self, setup_work_items):
            commit_headers = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that [fixes #2000 and #5000] "
                )
            ]
            resolved, _ = work_tracker.resolve_work_items_from_commit_headers(polaris_organization_key, commit_headers)
            assert len(resolved) == 1
            assert {'2000'} == {work_item['display_id'] for work_item in resolved[0]['work_items']}

        def it_omits_commits_where_there_are_no_matching_work_items(self, setup_work_items):
            commit_headers = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes [#2000 and #2002 ]"
                ),
                dict(
                    commit_key='B',
                    commit_message=" Do something that [fixes #5000 ]"
                )
            ]
            resolved, _ = work_tracker.resolve_work_items_from_commit_headers(polaris_organization_key, commit_headers)
            assert len(resolved) == 1





class TestResolveCommitsForWorkItems:

    class ContextGithubWorkItems:


        def it_resolves_commits_when_a_commit_message_contains_a_single_issue_reference(self, setup_work_items):
            commit_headers = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes #1000 "
                )
            ]
            _, work_item_commits = work_tracker.resolve_work_items_from_commit_headers(rails_organization_key, commit_headers)
            assert len(work_item_commits) == 1
            work_item = find_work_items(rails_work_items_source_key, ['1000'])[0]
            assert work_item_commits[0]['work_item_key'] == work_item.key
            assert work_item_commits[0]['commit_headers'] == commit_headers



        def it_resolves_work_items_when_a_commit_message_contains_a_multiple_issue_references(self, setup_work_items):
            commit_headers = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes #1000 and #1002 "
                )
            ]
            _, work_item_commits = work_tracker.resolve_work_items_from_commit_headers(rails_organization_key, commit_headers)
            assert len(work_item_commits) == 2
            work_items = find_work_items(rails_work_items_source_key, ['1000', '1002'])
            assert {work_item.key for work_item in work_items} == \
                   {work_item_commit['work_item_key'] for work_item_commit in work_item_commits}
            assert all([work_item_commit['commit_headers'] == commit_headers for work_item_commit in work_item_commits])


        def it_resolves_work_items_for_multiple_commits(self, setup_work_items):
            commit_headers = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes #1000 and #1002 "
                ),
                dict(
                    commit_key='B',
                    commit_message=" Do something that fixes #1003"
                )
            ]
            _, work_items_commits = work_tracker.resolve_work_items_from_commit_headers(rails_organization_key, commit_headers)
            assert len(work_items_commits) == 3

            work_item_1000 = find_work_items(rails_work_items_source_key, ['1000'])[0]
            work_item_1002 = find_work_items(rails_work_items_source_key, ['1002'])[0]
            work_item_1003 = find_work_items(rails_work_items_source_key, ['1003'])[0]
            work_items = [work_item_1000, work_item_1002, work_item_1003]

            assert {work_item.key for work_item in work_items} == \
                   {work_item_commit['work_item_key'] for work_item_commit in work_items_commits}

            for work_item_commits in work_items_commits:
                if work_item_commits['work_item_key'] == work_item_1000.key:
                    assert(work_item_commits['commit_headers']) == [commit_headers[0]]
                elif work_item_commits['work_item_key'] == work_item_1002.key:
                    assert(work_item_commits['commit_headers']) == [commit_headers[0]]
                elif work_item_commits['work_item_key'] == work_item_1003.key:
                    assert(work_item_commits['commit_headers']) == [commit_headers[1]]

        def it_omits_issue_references_where_there_is_no_matching_work_item(self, setup_work_items):
            commit_headers = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes #1000 and #5000 "
                )
            ]
            _, work_items_commits = work_tracker.resolve_work_items_from_commit_headers(rails_organization_key, commit_headers)
            assert len(work_items_commits) == 1
            work_item = find_work_items(rails_work_items_source_key, ['1000'])[0]
            assert work_items_commits[0]['work_item_key'] == work_item.key
            assert work_items_commits[0]['commit_headers'] == commit_headers


        def it_omits_commits_where_there_are_no_matching_work_items(self, setup_work_items):
            commit_headers = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes #1000 and #1002 "
                ),
                dict(
                    commit_key='B',
                    commit_message=" Do something that fixes #5000"
                )
            ]
            _, work_items_commits = work_tracker.resolve_work_items_from_commit_headers(rails_organization_key, commit_headers)
            assert len(work_items_commits) == 2
            assert all([work_item_commits['commit_headers'] == [commit_headers[0]] for work_item_commits in work_items_commits])


commit_header_common = dict(
    commit_message='A Change',
    commit_date=datetime.utcnow(),
    commit_date_tz_offset=0,
    committer_contributor_key=uuid.uuid4().hex,
    committer_contributor_name='Joe Blow',
    author_date=datetime.utcnow(),
    author_date_tz_offset=0,
    author_contributor_key=uuid.uuid4().hex,
    author_contributor_name='Billy Bob'
)


@pytest.yield_fixture()
def work_items_commits_fixture(setup_work_items):
    try:
        yield
    finally:
        db.connection().execute("delete from work_tracking.work_items_commits")
        db.connection().execute("delete from work_tracking.cached_commits")


class TestUpdateWorkItemsCommits:

    def it_updates_commits_for_the_work_item_when_there_is_just_a_single_commit_and_work_item(self, work_items_commits_fixture):
        work_item_1000 = find_work_items(rails_work_items_source_key, ['1000'])[0]
        work_tracker.update_work_items_commits(
            organization_key=rails_organization_key,
            repository_name='rails',
            work_items_commits=[
                dict(
                    work_item_key = work_item_1000.key,
                    commit_headers = [
                        dict(
                            commit_key='XXXXX',
                            **commit_header_common
                        )
                    ]
                )
            ]

        )
        with db.create_session() as session:
            assert session.connection.execute('select count(id) from work_tracking.cached_commits').scalar() == 1
            assert session.connection.execute('select count(*) from work_tracking.work_items_commits').scalar() == 1

    def it_updates_commits_for_the_work_item_when_there_are_multiple_commit_per_work_item(self, work_items_commits_fixture):
        work_item_1000 = find_work_items(rails_work_items_source_key, ['1000'])[0]
        work_tracker.update_work_items_commits(
            organization_key=rails_organization_key,
            repository_name='rails',
            work_items_commits=[
                dict(
                    work_item_key = work_item_1000.key,
                    commit_headers = [
                        dict(
                            commit_key='XXXXX',
                            **commit_header_common
                        ),
                        dict(
                            commit_key='YYYY',
                            **commit_header_common
                        )
                    ]
                )
            ]

        )
        with db.create_session() as session:
            assert session.connection.execute('select count(id) from work_tracking.cached_commits').scalar() == 2
            assert session.connection.execute('select count(*) from work_tracking.work_items_commits').scalar() == 2


    def it_works_for_multiple_work_items(self, work_items_commits_fixture):
        work_item_1000 = find_work_items(rails_work_items_source_key, ['1000'])[0]
        work_item_1001 = find_work_items(rails_work_items_source_key, ['1001'])[0]
        work_tracker.update_work_items_commits(
            organization_key=rails_organization_key,
            repository_name='rails',
            work_items_commits=[
                dict(
                    work_item_key = work_item_1000.key,
                    commit_headers = [
                        dict(
                            commit_key='XXXXX',
                            **commit_header_common
                        )
                    ]
                ),
                dict(
                    work_item_key=work_item_1001.key,
                    commit_headers=[
                        dict(
                            commit_key='YYYY',
                            **commit_header_common
                        )
                    ]
                )
            ]

        )
        with db.create_session() as session:
            assert session.connection.execute('select count(id) from work_tracking.cached_commits').scalar() == 2
            assert session.connection.execute('select count(*) from work_tracking.work_items_commits').scalar() == 2

    def it_does_not_create_duplicate_commits_when_a_commit_is_referenced_by_multiple_work_items(self, work_items_commits_fixture):
        work_item_1000 = find_work_items(rails_work_items_source_key, ['1000'])[0]
        work_item_1001 = find_work_items(rails_work_items_source_key, ['1001'])[0]
        work_tracker.update_work_items_commits(
            organization_key=rails_organization_key,
            repository_name='rails',
            work_items_commits=[
                dict(
                    work_item_key = work_item_1000.key,
                    commit_headers = [
                        dict(
                            commit_key='XXXX',
                            **commit_header_common
                        )
                    ]
                ),
                dict(
                    work_item_key=work_item_1001.key,
                    commit_headers=[
                        dict(
                            commit_key='XXXX',
                            **commit_header_common
                        )
                    ]
                )
            ]

        )
        with db.create_session() as session:
            assert session.connection.execute('select count(id) from work_tracking.cached_commits').scalar() == 1
            assert session.connection.execute('select count(*) from work_tracking.work_items_commits').scalar() == 2

    def it_only_caches_new_commits(self, work_items_commits_fixture):
        work_item_1000 = find_work_items(rails_work_items_source_key, ['1000'])[0]
        work_item_1001 = find_work_items(rails_work_items_source_key, ['1001'])[0]
        db.connection().execute(
            cached_commits.insert([
                dict(
                    commit_key='XXXX',
                    repository_name='rails',
                    organization_key=rails_organization_key,
                    **commit_header_common
                )
            ])
        )
        work_tracker.update_work_items_commits(
            organization_key=rails_organization_key,
            repository_name='rails',
            work_items_commits=[
                dict(
                    work_item_key = work_item_1000.key,
                    commit_headers = [
                        dict(
                            commit_key='XXXX',
                            **commit_header_common
                        )
                    ]
                ),
                dict(
                    work_item_key=work_item_1001.key,
                    commit_headers=[
                        dict(
                            commit_key='YYYY',
                            **commit_header_common
                        )
                    ]
                )
            ]

        )
        with db.create_session() as session:
            assert session.connection.execute('select count(id) from work_tracking.cached_commits').scalar() == 2
            assert session.connection.execute('select count(*) from work_tracking.work_items_commits').scalar() == 2



