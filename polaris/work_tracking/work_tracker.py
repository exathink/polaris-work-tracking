# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar



from polaris.work_tracking.db import api

from polaris.work_tracking.work_items_source_factory import create_work_items_source, get_work_items_resolver

def sync_work_items(token_provider, work_items_source_key):
    work_items_source = create_work_items_source(token_provider, work_items_source_key)

    import_count = 0
    for work_items in work_items_source.fetch_work_items_to_sync():
        api.sync_work_items(work_items_source_key, work_items)
        import_count = import_count + len(work_items)

    return import_count

def resolve_work_items_from_commit_summaries(organization_key, commit_summaries):
    work_item_resolver = get_work_items_resolver(organization_key)
    if work_item_resolver:
        commit_work_items_to_resolve = {}
        for commit_summary in commit_summaries:
            display_ids = work_item_resolver.resolve(commit_summary['commit_message'])
            if len(display_ids) > 0:
                commit_work_items_to_resolve[commit_summary['commit_key']] = display_ids

        work_items_to_resolve = set()
        for display_ids in commit_work_items_to_resolve.values():
            work_items_to_resolve.update(display_ids)

        work_items_map = api.resolve_work_items_by_display_ids(organization_key, work_items_to_resolve)

        resolved = []
        for commit_key, display_ids in commit_work_items_to_resolve.items():
            resolved_work_items = []
            for display_id in display_ids:
                if display_id in work_items_map:
                    resolved_work_items.append(work_items_map[display_id])

            if len(resolved_work_items) > 0:
                resolved.append(
                    dict(
                        commit_key=commit_key,
                        work_items=resolved_work_items
                    )
                )

        return resolved







