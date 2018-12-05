# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from polaris.common import db
from polaris.work_tracking.db.model import WorkItemsSource
from polaris.work_tracking.integrations.github import GithubIssuesWorkItemsSource
from polaris.work_tracking.integrations.pivotal_tracker import PivotalTrackerWorkItemsSource

def get_work_items_source_impl(token_provider, work_items_source):
    work_items_source_impl = None

    if work_items_source.integration_type in ['github', 'github_enterprise']:
        work_items_source_impl = GithubIssuesWorkItemsSource.create(token_provider, work_items_source)
    elif work_items_source.integration_type in ['pivotal_tracker']:
        work_items_source_impl = PivotalTrackerWorkItemsSource.create(token_provider, work_items_source)

    assert work_items_source_impl is not None, f'Could not determine work_items_source_implementation for work_items_source_key {work_items_source_key}'
    return work_items_source_impl

def get_work_items_resolver(organization_key):
    resolver = None
    with db.orm_session() as session:
        work_item_sources = WorkItemsSource.find_by_organization_key(session, organization_key)
        if work_item_sources:
            work_items_source = work_item_sources[0]
            if work_items_source.integration_type in ['github', 'github_enterprise']:
                resolver = GithubIssuesWorkItemsSource.WorkItemResolver
            elif work_items_source.integration_type in ['pivotal_tracker']:
                resolver = PivotalTrackerWorkItemsSource.WorkItemResolver

    return resolver