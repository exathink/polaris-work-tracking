# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Priya Mukundan

from polaris.common import db
from polaris.work_tracking.db import model
from .fixtures.jira_fixtures import *
from polaris.utils.collections import object_to_dict, Fixture


class TestModel:




    @pytest.fixture()
    def setup(self, jira_work_items_fixture, cleanup):
        work_items, work_items_source, jira_project_id, connector_key = jira_work_items_fixture

        yield Fixture(
            work_items=work_items

        )

    def it_updates_work_item(self, setup):
        #update this test every time a new attribute is added; add a separate instance of update for each
        #attribute since even if one attribute is updated, the function returns True
        fixture = setup

        work_item = [wi for wi in fixture.work_items][0]

        # Check for priority

        work_item_data = dict()
        work_item_data['priority']= 'Medium'
        updated = work_item.update(work_item_data)
        assert updated


