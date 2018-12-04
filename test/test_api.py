# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from polaris.common import db
from polaris.work_tracking.db import api


class TestSyncWorkItems:

    def it_imports_work_items_when_the_source_has_no_work_items(self,setup_work_items, new_work_items, cleanup_empty):
        _, work_items_sources = setup_work_items
        empty_source = work_items_sources['empty']
        created = api.sync_work_items(empty_source.key, work_item_list=new_work_items)
        assert len(created) == len(new_work_items)
        assert db.connection().execute(
            f"select count(id) from work_tracking.work_items where work_items_source_id={empty_source.id}"
        ).scalar() == len(new_work_items)

    def it_does_not_create_work_items_that_match_existing_items_by_source_id(self,setup_work_items, new_work_items, cleanup_empty):
        _, work_items_sources = setup_work_items
        empty_source = work_items_sources['empty']
        # Import once
        api.sync_work_items(empty_source.key, work_item_list=new_work_items)
        # Now import the same set again
        created = api.sync_work_items(empty_source.key, work_item_list=new_work_items)
        assert len(created) == 0
        assert db.connection().execute(
            f"select count(id) from work_tracking.work_items where work_items_source_id={empty_source.id}"
        ).scalar() == len(new_work_items)


    def it_updates_existing_work_items_that_match_incoming_items_by_source_id(self,setup_work_items, new_work_items, cleanup_empty):
        _, work_items_sources = setup_work_items
        empty_source = work_items_sources['empty']
        # Import once
        api.sync_work_items(empty_source.key, work_item_list=new_work_items)
        # Now import updated versions of the same source work items
        created = api.sync_work_items(empty_source.key, work_item_list=[
            {**work_item, **dict(source_state='closed')}
            for work_item in new_work_items
        ])
        assert len(created) == 0
        assert db.connection().execute(
            f"select count(id) from work_tracking.work_items where work_items_source_id={empty_source.id} and source_state='closed'"
        ).scalar() == len(new_work_items)

