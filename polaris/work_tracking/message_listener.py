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
from polaris.messaging.messages import CommitsCreated, CommitWorkItemsResolved, WorkItemsCommitsResolved
from polaris.messaging.topics import CommitsTopic, WorkItemsTopic
from polaris.messaging.message_consumer import MessageConsumer

from polaris.work_tracking import work_tracker
from polaris.common import db


logger = logging.getLogger('polaris.work_tracking.message_listener')

def process_commits_created(message):
    organization_key = message['organization_key']
    repository_name = message['repository_name']
    logger.info(f"Processing  commit_history_imported"
                f"Organization: {organization_key}"
                f"Repository: {repository_name}")

    resolved_work_items = work_tracker.resolve_work_items_from_commit_summaries(
        organization_key,
        message['new_commits']
    )
    if resolved_work_items is not None:
        logger.info(f'Resolved new work_items for {len(resolved_work_items[0])} commits for organization {organization_key} and repository {repository_name}')
        return dict(
           organization_key=organization_key,
           repository_name=repository_name,
           commit_work_items=resolved_work_items[0]
       ), dict(
            organization_key=organization_key,
            repository_name=repository_name,
            work_items_commits=resolved_work_items[1]
        )


def commits_topic_dispatch(channel, method, properties, body):
    if CommitsCreated.message_type == method.routing_key:
        message = CommitsCreated(receive=body)
        resolved = process_commits_created(message.dict)
        if resolved:
           commit_work_items_resolved_message = CommitWorkItemsResolved(send=resolved[0], in_response_to=message)
           CommitsTopic(channel).publish(message=commit_work_items_resolved_message)

           work_items_commits_resolved_message = WorkItemsCommitsResolved(send=resolved[1], in_response_to=message)
           WorkItemsTopic(channel).publish(message=work_items_commits_resolved_message)
           return commit_work_items_resolved_message, work_items_commits_resolved_message

#-------------------------------------------------
#
# ------------------------------------------------

def process_work_items_commits_resolved(received):
    logger.info("Received message work_items_commits_resolved")

def work_items_topic_dispatch(channel, method, properties, body):
    if WorkItemsCommitsResolved.message_type == method.routing_key:
        resolved = process_work_items_commits_resolved(body)

        return resolved

# ----------
# Initialization
# --------------



def init_consumer(channel):
    commits_topic = CommitsTopic(channel, create=True)
    commits_topic.add_subscriber(
        subscriber_queue='commits_work_items',
        message_classes=[
            CommitsCreated
        ],
        callback=commits_topic_dispatch,
        exclusive=False,
        no_ack=True
    )

    work_items_topic = WorkItemsTopic(channel, create=True)
    work_items_topic.add_subscriber(
        subscriber_queue='work_items_work_items',
        message_classes=[
            WorkItemsCommitsResolved
        ],
        callback=work_items_topic_dispatch,
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






