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
from polaris.messaging.utils import publish, init_topics_to_publish, shutdown
from polaris.messaging.messages import ImportWorkItems
from logging import getLogger

logger = getLogger('polaris.work_tracking.sync_agent')


class WorkTrackingAgent(Agent):

    def run(self):
        self.loop(self.sync_work_item_sources)

    def sync_work_item_sources(self):
        logger.info("Checking for work items sources to sync")
        found = False
        for source in api.get_work_items_sources_to_sync():
            found = True
            publish(
                WorkItemsTopic,
                ImportWorkItems(send=source)
            )
            if self.exit_signal_received:
                shutdown()
                break

        if not found:
            logger.info("No sources found to sync...")
        return True



def start(name=None, poll_interval=None):
    agent = WorkTrackingAgent(
        name=name,
        poll_interval=poll_interval
    )
    logger.info("Starting agent.")
    agent.run()


if __name__ == '__main__':

    config_logging()
    logger.info("Connecting to database....")
    db.init()
    logger.info("Initializing messaging..")
    init_topics_to_publish(WorkItemsTopic)

    argh.dispatch_commands([
        start
    ])