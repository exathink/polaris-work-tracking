# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import argh
from polaris.utils.agent import Agent
from polaris.utils.logging import config_logging

from polaris.common import db
from polaris.work_tracking.db import api
from polaris.messaging.topics import WorkItemsTopic
from polaris.messaging.utils import publish
from polaris.messaging.messages import ImportWorkItems


class WorkTrackingAgent(Agent):

    def run(self):
        self.loop(self.sync_work_item_sources)

    @staticmethod
    def sync_work_item_sources():
        for source in api.get_work_items_sources_to_sync():
            publish(
                WorkItemsTopic,
                ImportWorkItems(send=source)
            )

        return True


def start(name=None, poll_interval=None):
    agent = WorkTrackingAgent(
        name=name,
        poll_interval=poll_interval
    )
    agent.run()


if __name__ == '__main__':

    config_logging()
    db.init()

    argh.dispatch_commands([
        start
    ])