# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging

from polaris.common import db
from polaris.messaging.message_consumer import MessageConsumer
from polaris.messaging.messages import ImportWorkItems, WorkItemsCreated, WorkItemsUpdated
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
            total = 0
            messages = []
            for created, updated in self.process_import_work_items(message):
                if len(created) > 0:
                    total = total + len(created)
                    logger.info(f'{len(created)} new work_items')
                    created_message = WorkItemsCreated(send=dict(
                        organization_key=message['organization_key'],
                        work_items_source_key=message['work_items_source_key'],
                        new_work_items=created
                    ))
                    WorkItemsTopic(channel).publish(created_message)
                    messages.append(created_message)

                if len(updated) > 0:
                    total = total + len(updated)
                    logger.info(f'{len(updated)} updated work_items')
                    updated_message = WorkItemsUpdated(send=dict(
                        organization_key=message['organization_key'],
                        work_items_source_key=message['work_items_source_key'],
                        updated_work_items=updated
                    ))
                    WorkItemsTopic(channel).publish(updated_message)
                    messages.append(updated_message)

            logger.info(f'{total} work items processed')
            return messages

    def process_import_work_items(self, message):
        work_items_source_key = message['work_items_source_key']
        logger.info(f"Processing  {message.message_type}: "
                    f" Work Items Source Key : {work_items_source_key}")

        for work_items in work_tracker.sync_work_items(self.consumer_context.token_provider, work_items_source_key):
            created = []
            updated = []
            for work_item in work_items:
                if work_item['is_new']:
                    created.append(work_item)
                else:
                    updated.append(work_item)

            yield created, updated


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






