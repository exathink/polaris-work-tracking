# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2016-2017) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from sqlalchemy import cast, Text, func, and_
from datetime import datetime, timedelta




def work_items_source_info_columns(work_items_sources):
    return [
        work_items_sources.c.url,
        work_items_sources.c.description,
        work_items_sources.c.account_key,
        work_items_sources.c.organization_key,
        work_items_sources.c.integration_type,
        work_items_sources.c.import_state
    ]


def commits_connection_apply_time_window_filters(select_stmt, commits,  **kwargs):
    before = None
    if 'before' in kwargs:
        before = kwargs['before']

    if 'days' in kwargs and kwargs['days'] > 0:
        if before:
            commit_window_start = before - timedelta(days=kwargs['days'])
            return select_stmt.where(
                and_(
                    commits.c.commit_date >= commit_window_start,
                    commits.c.commit_date <= before
                )
            )
        else:
            commit_window_start = datetime.utcnow() - timedelta(days=kwargs['days'])
            return select_stmt.where(
                    commits.c.commit_date >= commit_window_start
                )
    elif before:
        return select_stmt.where(
            commits.c.commit_date <= before
        )
    else:
        return select_stmt

