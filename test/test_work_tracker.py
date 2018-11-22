# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from polaris.work_tracking import work_tracker
from test.constants import *

class TestResolveWorkItemsFromCommits:

    class ContextGithubWorkItems:

        def it_resolves_work_items_when_a_commit_message_contains_a_single_issue_reference(self, setup_work_items):
            commit_summaries = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes #1000 "
                )
            ]
            resolved = work_tracker.resolve_work_items_from_commit_summaries(rails_organization_key, commit_summaries)
            assert len(resolved) == 1
            assert resolved[0]['commit_key'] == 'A'
            assert resolved[0]['work_items'][0]['display_id'] == '1000'

        def it_resolves_work_items_when_a_commit_message_contains_a_multiple_issue_references(self, setup_work_items):
            commit_summaries = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes #1000 and #1002 "
                )
            ]
            resolved = work_tracker.resolve_work_items_from_commit_summaries(rails_organization_key, commit_summaries)
            assert len(resolved) == 1
            assert resolved[0]['commit_key'] == 'A'
            assert {'1000', '1002'} == {work_item.display_id for work_item in resolved[0]['work_items']}


        def it_resolves_work_items_for_multiple_commits(self, setup_work_items):
            commit_summaries = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes #1000 and #1002 "
                ),
                dict(
                    commit_key='B',
                    commit_message=" Do something that fixes #1003"
                )
            ]
            resolved = work_tracker.resolve_work_items_from_commit_summaries(rails_organization_key, commit_summaries)
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
            commit_summaries = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes #1000 and #5000 "
                )
            ]
            resolved = work_tracker.resolve_work_items_from_commit_summaries(rails_organization_key, commit_summaries)
            assert len(resolved) == 1
            assert {'1000'} == {work_item.display_id for work_item in resolved[0]['work_items']}

        def it_omits_commits_where_there_are_no_matching_work_items(self, setup_work_items):
            commit_summaries = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes #1000 and #1002 "
                ),
                dict(
                    commit_key='B',
                    commit_message=" Do something that fixes #5000"
                )
            ]
            resolved = work_tracker.resolve_work_items_from_commit_summaries(rails_organization_key, commit_summaries)
            assert len(resolved) == 1




    class ContextPivotalWorkItems:

        def it_resolves_work_items_when_a_commit_message_contains_a_single_issue_reference(self, setup_work_items):
            commit_summaries = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes [#2000 ]"
                )
            ]
            resolved = work_tracker.resolve_work_items_from_commit_summaries(polaris_organization_key, commit_summaries)
            assert len(resolved) == 1
            assert resolved[0]['commit_key'] == 'A'
            assert resolved[0]['work_items'][0]['display_id'] == '2000'

        def it_resolves_work_items_when_a_commit_message_contains_a_multiple_issue_references(self, setup_work_items):
            commit_summaries = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that [fixes #2000 and #2002] "
                )
            ]
            resolved = work_tracker.resolve_work_items_from_commit_summaries(polaris_organization_key, commit_summaries)
            assert len(resolved) == 1
            assert resolved[0]['commit_key'] == 'A'
            assert {'2000', '2002'} == {work_item.display_id for work_item in resolved[0]['work_items']}


        def it_resolves_work_items_for_multiple_commits(self, setup_work_items):
            commit_summaries = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes [#2000 and #2002] "
                ),
                dict(
                    commit_key='B',
                    commit_message=" Do something that [fixes #2003]"
                )
            ]
            resolved = work_tracker.resolve_work_items_from_commit_summaries(polaris_organization_key, commit_summaries)
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
            commit_summaries = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that [fixes #2000 and #5000] "
                )
            ]
            resolved = work_tracker.resolve_work_items_from_commit_summaries(polaris_organization_key, commit_summaries)
            assert len(resolved) == 1
            assert {'2000'} == {work_item.display_id for work_item in resolved[0]['work_items']}

        def it_omits_commits_where_there_are_no_matching_work_items(self, setup_work_items):
            commit_summaries = [
                dict(
                    commit_key='A',
                    commit_message=" Do something that fixes [#2000 and #2002 ]"
                ),
                dict(
                    commit_key='B',
                    commit_message=" Do something that [fixes #5000 ]"
                )
            ]
            resolved = work_tracker.resolve_work_items_from_commit_summaries(polaris_organization_key, commit_summaries)
            assert len(resolved) == 1
