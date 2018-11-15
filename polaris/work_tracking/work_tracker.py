# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar


from polaris.common import db
from polaris.work_tracking.db.model import WorkItemsSource
from polaris.work_tracking.integrations.github import GithubIssuesWorkItemsSource
from polaris.work_tracking.db.api import import_work_items as db_import_work_items


def import_work_items(token_provider, work_items_source_key):

    work_items_source_impl = None
    latest_created = None
    with db.orm_session() as session:
        session.expire_on_commit=False
        work_items_source = WorkItemsSource.find_by_work_items_source_key(session, work_items_source_key)
        latest_created = work_items_source.latest_work_item_creation_date

    if work_items_source.integration_type in ['github', 'github_enterprise']:
        work_items_source_impl = GithubIssuesWorkItemsSource.create(token_provider, work_items_source)
    assert work_items_source_impl is not None, f'Could not determine work_items_source_implementation for work_items_source_key {work_items_source_key}'

    import_count = 0
    for work_items in work_items_source_impl.fetch_new_work_items(created_since=latest_created):

        db_import_work_items(work_items_source_key, work_items)
        import_count = import_count + len(work_items)

    return import_count

