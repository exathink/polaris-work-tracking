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

def create_work_items_source(token_provider, work_items_source_key):
    work_items_source_impl = None
    with db.orm_session() as session:
        session.expire_on_commit = False
        work_items_source = WorkItemsSource.find_by_work_items_source_key(session, work_items_source_key)
        if work_items_source.integration_type in ['github', 'github_enterprise']:
            work_items_source_impl = GithubIssuesWorkItemsSource.create(token_provider, work_items_source)
        elif work_items_source.integration_type in ['pivotal_tracker']:
            work_items_source_impl = PivotalTrackerWorkItemsSource.create(token_provider, work_items_source)

    assert work_items_source_impl is not None, f'Could not determine work_items_source_implementation for work_items_source_key {work_items_source_key}'
    return work_items_source_impl
