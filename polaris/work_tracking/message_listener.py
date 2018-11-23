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
from polaris.messaging.utils import polaris_mq_connection, unpack_message, pack_message, publish
from polaris.messaging.messages import MessageTypes, CommitHistoryImported, CommitWorkItemsResolved
from polaris.utils.exceptions import SchemaValidationError
from polaris.work_tracking import work_tracker
from polaris.common import db


logger = logging.getLogger('polaris.work_tracking.message_listener')

def process_commit_history_imported(message):
    request = CommitHistoryImported()
    message = request.loads(message)
    organization_key = message['organization_key']
    repository_name = message['repository_name']
    logger.info(f"Processing  "
                f"{MessageTypes.commit_history_imported} for "
                f"Organization: {organization_key}"
                f"Repository: {repository_name}")

    resolved_work_items = work_tracker.resolve_work_items_from_commit_summaries(
        organization_key,
        message['commit_summaries']
    )
    if resolved_work_items is not None:
        response = dict(
            organization_key=organization_key,
            repository_name=repository_name,
            commit_work_items=resolved_work_items
        )
        return response



def dispatch(body):
    message_type, payload = unpack_message(body)
    try:
        if message_type == MessageTypes.commit_history_imported:

            response_message_type = MessageTypes.commit_work_items_resolved
            response = process_commit_history_imported(message=payload)
            response_message = pack_message(
                message_type=response_message_type,
                payload=CommitWorkItemsResolved().dumps(response)
            )
            publish(
                exchange='commits',
                message=response_message,
                routing_key=response_message_type
            )
            logger.info(f'Published {response_message_type}')
            return response_message

    except SchemaValidationError as exc:
        logger.error(f"Message {body} failed schema validation: {str(exc)}")




def dispatch_callback(channel, method, properties, body):
   dispatch(body)

def init_consumer(channel):
    channel.exchange_declare(exchange='commits', exchange_type='fanout')
    channel.queue_declare(queue='commit_issues', exclusive=False)
    channel.queue_bind(exchange='commits', queue='commit_issues')
    channel.basic_consume(dispatch_callback, queue='commit_issues', no_ack=True)

def cleanup(channel, connection):
    channel.stop_consuming()
    channel.close()
    connection.close()

if __name__ == "__main__":
    config_logging()
    config_provider = get_config_provider()

    logger.info('Connecting to polaris db...')
    db.init(config_provider.get('POLARIS_DB_URL'))

    with polaris_mq_connection() as connection:
        channel = connection.channel()
        init_consumer(channel)
        signal.signal(signal.SIGTERM, lambda: cleanup(channel, connection))
        logger.info('Listening for messages..')
        try:
            channel.start_consuming()
        except Exception as exc:
            logger.warning(str(exc))






