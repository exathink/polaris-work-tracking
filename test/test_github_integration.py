# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from polaris.utils.work_tracking import GithubWorkItemResolver

class TestCommitWorkItemResolution:


    def it_resolves_a_commit_with_a_single_work_item_id(self):
        commit_message = "This fixes issue #2378. No other animals were harmed"


        resolved = GithubWorkItemResolver.resolve(commit_message)

        assert len(resolved) == 1
        assert resolved[0] == '2378'

    def it_resolves_a_commit_with_multiple_work_item_ids(self):
        commit_message = "This fixes issue #2378 and #24532 No other animals were harmed"



        resolved = GithubWorkItemResolver.resolve(commit_message)

        assert len(resolved) == 2
        assert resolved == ['2378', '24532']


