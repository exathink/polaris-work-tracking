# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging
import signal


from polaris.utils.logging import config_logging
from polaris.utils.config import get_config_provider
from polaris.messaging.utils import polaris_mq_connection, shutdown
from polaris.messaging.messages import CommitHistoryImported, CommitWorkItemsResolved
from polaris.messaging.topics import CommitsTopic
from polaris.messaging.message_consumer import MessageConsumer

from polaris.work_tracking import work_tracker
from polaris.common import db


logger = logging.getLogger('polaris.work_tracking.message_listener')

def process_commit_history_imported(received):
    message = CommitHistoryImported(receive=received)
    payload = message.dict
    organization_key = payload['organization_key']
    repository_name = payload['repository_name']
    logger.info(f"Processing  "
                f"{message.message_type} for "
                f"Organization: {organization_key}"
                f"Repository: {repository_name}")

    resolved_work_items = work_tracker.resolve_work_items_from_commit_summaries(
        organization_key,
        payload['commit_summaries']
    )
    if resolved_work_items is not None:
        logger.info(f'Resolved new work_items for {len(resolved_work_items)} commits for organization {organization_key} and repository {repository_name}')
        return dict(
           organization_key=organization_key,
           repository_name=repository_name,
           commit_work_items=resolved_work_items
       )


def commits_topic_dispatch(channel, method, properties, body):
    if CommitHistoryImported.message_type == method.routing_key:
       resolved = process_commit_history_imported(body)
       if resolved:
           response_message = CommitWorkItemsResolved(send=resolved)
           CommitsTopic(channel).publish(message=response_message)
           return response_message


# -------------
# Initialization
# --------------



def init_consumer(channel):
    commits_topic = CommitsTopic(channel, create=True)
    commits_topic.add_subscriber(
        subscriber_queue='commits_work_items',
        message_classes=[
            CommitHistoryImported
        ],
        callback=commits_topic_dispatch,
        exclusive=False,
        no_ack=True
    )








if __name__ == "__main__":
    config_logging()
    config_provider = get_config_provider()

    logger.info('Connecting to polaris db...')
    db.init(config_provider.get('POLARIS_DB_URL'))

    MessageConsumer(
        name='polaris.work_tracking.message_listener',
        init_consumer = init_consumer
    ).start_consuming()






