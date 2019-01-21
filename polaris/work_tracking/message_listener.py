# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging

from polaris.common import db
from polaris.messaging.message_consumer import MessageConsumer
from polaris.messaging.messages import \
    ImportWorkItems, \
    WorkItemsCreated
from polaris.messaging.topics import WorkItemsTopic, TopicSubscriber
from polaris.utils.config import get_config_provider
from polaris.utils.logging import config_logging
from polaris.utils.token_provider import get_token_provider
from polaris.work_tracking import work_tracker

logger = logging.getLogger('polaris.work_tracking.message_listener')







#-------------------------------------------------
#
# ------------------------------------------------

class WorkItemsTopicSubscriber(TopicSubscriber):
    def __init__(self, channel):
        super().__init__(
            topic = WorkItemsTopic(channel, create=True),
            subscriber_queue='work_items_work_items',
            message_classes=[
                #Commands
                ImportWorkItems
            ],
            exclusive=False
        )

    def dispatch(self, channel, message):

        if ImportWorkItems.message_type == message.message_type:
            result = self.process_import_work_items(message)
            if result:
                work_items_created = None
                if result['created'] > 0:
                    work_items_created = WorkItemsCreated(send=result, in_response_to=message)
                    WorkItemsTopic(channel).publish(work_items_created)
                return work_items_created


    def process_import_work_items(self, message):
        work_items_source_key = message['work_items_source_key']
        logger.info(f"Processing  {message.message_type}: "
                    f" Work Items Source Key : {work_items_source_key}")

        result = work_tracker.sync_work_items(self.consumer_context.token_provider, work_items_source_key)
        return dict(
            work_items_source_key=work_items_source_key,
            **result
        )


if __name__ == "__main__":
    config_logging()
    config_provider = get_config_provider()

    logger.info('Connecting to polaris db...')
    db.init(config_provider.get('POLARIS_DB_URL'))
    token_provider = get_token_provider()

    MessageConsumer(
        name='polaris.work_tracking.message_listener',
        topic_subscriber_classes=[
            WorkItemsTopicSubscriber
        ],
        token_provider=token_provider
    ).start_consuming()






