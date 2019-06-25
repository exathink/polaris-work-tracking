# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2019) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from polaris.graphql.interfaces import NamedNode
from ..interfaces import WorkItemsSourceInfo

from sqlalchemy import select, bindparam
from polaris.work_tracking.db.model import work_items_sources


class ConnectorWorkItemsSourceNodes:
    interfaces = (NamedNode, WorkItemsSourceInfo)

    @staticmethod
    def selectable(**kwargs):
        return select([
            work_items_sources.c.id,
            work_items_sources.c.key.label('key'),
            work_items_sources.c.name,
            work_items_sources.c.url,
            work_items_sources.c.description,
            work_items_sources.c.account_key,
            work_items_sources.c.organization_key,
            work_items_sources.c.integration_type
        ]).select_from(
            work_items_sources
        ).where(work_items_sources.c.connector_key == bindparam('key'))


