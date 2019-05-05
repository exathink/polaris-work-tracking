# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from polaris.common.enums import WorkTrackingIntegrationType
from polaris.utils.exceptions import ProcessingException
from polaris.work_tracking.integrations.atlassian.jira_work_items_source import JiraWorkItemsSource
from polaris.work_tracking.integrations.github import GithubIssuesWorkItemsSource
from polaris.work_tracking.integrations.pivotal_tracker import PivotalTrackerWorkItemsSource


def get_work_items_source_impl(token_provider, work_items_source):

    if work_items_source.integration_type == WorkTrackingIntegrationType.github.value:
        work_items_source_impl = GithubIssuesWorkItemsSource.create(token_provider, work_items_source)
    elif work_items_source.integration_type == WorkTrackingIntegrationType.pivotal.value:
        work_items_source_impl = PivotalTrackerWorkItemsSource.create(token_provider, work_items_source)
    elif work_items_source.integration_type == WorkTrackingIntegrationType.jira.value:
        work_items_source_impl = JiraWorkItemsSource.create(token_provider, work_items_source)
    else:
        raise ProcessingException(
            f'Could not determine work_items_source_implementation for work_items_source_key {work_items_source.key}'
        )

    return work_items_source_impl






