# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal

import logging
from enum import Enum
from polaris.integrations.gitlab import GitlabConnector
from polaris.utils.exceptions import ProcessingException
from polaris.work_tracking import connector_factory

logger = logging.getLogger('polaris.work_tracking.gitlab')


class GitlabWorkTrackingConnector(GitlabConnector):
    pass


class GitlabWorkItemSourceType(Enum):
    repository_issues = 'repository_issues'


class GitlabIssuesWorkItemsSource:

    @staticmethod
    def create(token_provider, work_items_source):
        if work_items_source.work_items_source_type == GitlabWorkItemSourceType.repository_issues.value:
            return GitlabRepositoryIssues(token_provider, work_items_source)

        else:
            raise ProcessingException(f"Unknown work items source type {work_items_source.work_items_source_type}")


class GitlabRepositoryIssues(GitlabIssuesWorkItemsSource):

    def __init__(self, token_provider, work_items_source):
        self.work_items_source = work_items_source
        self.last_updated = work_items_source.latest_work_item_update_timestamp

        self.gitlab_connector = connector_factory.get_connector(
            connector_key=self.work_items_source.connector_key
        )
