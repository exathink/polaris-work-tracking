# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging

from polaris.common import db
from polaris.work_tracking.db import api
from polaris.work_tracking.db.model import WorkItemsSource
from polaris.work_tracking.work_items_source_factory import get_work_items_source_impl, get_work_items_resolver

logger = logging.getLogger('polaris.work_tracking.work_tracker')


def sync_work_items(token_provider, work_items_source_key):
    with db.orm_session() as session:
        session.expire_on_commit = False
        work_items_source = WorkItemsSource.find_by_work_items_source_key(session, work_items_source_key)
        work_items_source_impl = get_work_items_source_impl(token_provider, work_items_source)

    for work_items in work_items_source_impl.fetch_work_items_to_sync():
        yield api.sync_work_items(work_items_source_key, work_items) or []




def resolve_work_items_from_commit_headers(organization_key, commit_headers):
    work_item_resolver = get_work_items_resolver(organization_key)
    if work_item_resolver:
        # hash commit summaries by commit key for downstream processing
        # and map each commit to the display_ids of any work_item references in
        # the commit message.
        commit_headers_to_resolve = {
            commit_summary['commit_key']:
                dict(
                    commit_summary=commit_summary,
                    work_item_display_ids=work_item_resolver.resolve(commit_summary['commit_message'])
                )
            for commit_summary in commit_headers
        }
        # Take the union of all the display_ids in the commit messages above
        work_items_to_resolve = set()
        for resolve_data in commit_headers_to_resolve.values():
                work_items_to_resolve.update(resolve_data['work_item_display_ids'])

        # resolve the display ids to work_items, we will interpolate commits into this
        # work items returned here.
        work_items_map = api.resolve_work_items_by_display_ids(organization_key, work_items_to_resolve)
        # initialize the list that will hold the reverse mapping of commits to work items.
        commits_to_work_items = []
        # Do the bidirectional resoution of work items to commits and commits to work items.
        for commit_key, resolve_data in commit_headers_to_resolve.items():
            commit_work_items = []
            for display_id in resolve_data['work_item_display_ids']:
                if display_id in work_items_map:
                    work_item = work_items_map[display_id]
                    # associate work_item with commit
                    commit_work_items.append(work_item)
                    # associate commit summary with work_items
                    work_item['commit_headers'] = work_item.get('commit_headers', [])
                    work_item['commit_headers'].append(
                        commit_headers_to_resolve[commit_key]['commit_summary']
                    )


            if len(commit_work_items) > 0:
                commits_to_work_items.append(
                    dict(
                        commit_key=commit_key,
                        work_items=commit_work_items
                    )
                )
        # build the reverse mapping output data structure
        work_items_to_commits = [
            dict(
                work_item_key=work_item['work_item_key'],
                commit_headers=work_item['commit_headers']
            )
            for work_item in work_items_map.values()
        ]

        # return both mappings.
        return commits_to_work_items, work_items_to_commits




def update_work_items_commits(organization_key, repository_name, work_items_commits):
    return api.update_work_items_commits(organization_key, repository_name, work_items_commits)



