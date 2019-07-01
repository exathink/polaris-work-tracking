# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2019) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from polaris.graphql.interfaces import NamedNode
from ..interfaces import WorkItemsSourceInfo, WorkItemCount
from .sql_expressions import work_items_source_info_columns
from sqlalchemy import select, bindparam, func
from polaris.work_tracking.db.model import work_items_sources, work_items


class WorkItemsSourceNode:
    interfaces = (NamedNode, WorkItemsSourceInfo)

    @staticmethod
    def selectable(**kwargs):
        return select([
            work_items_sources.c.id,
            work_items_sources.c.key.label('key'),
            work_items_sources.c.name,
            *work_items_source_info_columns(work_items_sources)

        ]).select_from(
            work_items_sources
        ).where(work_items_sources.c.key == bindparam('key'))


class WorkItemsSourceWorkItemCount:
    interface = (WorkItemCount)

    @staticmethod
    def selectable(work_items_source_node, **kwargs):
        return select([
            work_items_source_node.c.id,
            func.count(work_items.c.id).label('work_item_count')
        ]).select_from(
            work_items_source_node.outerjoin(
                work_items, work_items_source_node.c.id == work_items.c.work_items_source_id
            )
        ).group_by(
            work_items_source_node.c.id
        )
