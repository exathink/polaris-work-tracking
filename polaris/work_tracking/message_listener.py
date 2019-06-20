# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import json
import logging

from polaris.common import db
from polaris.messaging.message_consumer import MessageConsumer
from polaris.messaging.messages import ImportWorkItems, WorkItemsCreated, WorkItemsUpdated, WorkItemsSourceCreated
from polaris.messaging.topics import WorkItemsTopic, TopicSubscriber
from polaris.messaging.utils import raise_message_processing_error
from polaris.utils.config import get_config_provider
from polaris.utils.exceptions import ProcessingException
from polaris.utils.logging import config_logging
from polaris.utils.token_provider import get_token_provider
from polaris.work_tracking import commands
from polaris.work_tracking.integrations.atlassian import jira_message_handler
from polaris.work_tracking.messages.atlassian_connect_work_item_event import AtlassianConnectWorkItemEvent
from polaris.work_tracking.messages.connector_event import ConnectorEvent

logger = logging.getLogger('polaris.work_tracking.message_listener')


# -------------------------------------------------
#
# ------------------------------------------------


class WorkItemsTopicSubscriber(TopicSubscriber):
    def __init__(self, channel, publisher=None):
        super().__init__(
            topic=WorkItemsTopic(channel, create=True),
            subscriber_queue='work_items_work_items',
            message_classes=[
                # Events
                WorkItemsSourceCreated,
                AtlassianConnectWorkItemEvent,
                ConnectorEvent,
                # Commands
                ImportWorkItems
            ],
            publisher=publisher,
            exclusive=False
        )

    def dispatch(self, channel, message):

        if WorkItemsSourceCreated.message_type == message.message_type:
            import_message = ImportWorkItems(send=dict(
                organization_key=message['organization_key'],
                work_items_source_key=message['work_items_source']['key']
            ), in_response_to=message
            )
            self.publish(WorkItemsTopic, import_message)
            return import_message

        elif ImportWorkItems.message_type == message.message_type:
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
                    self.publish(WorkItemsTopic, created_message)
                    messages.append(created_message)

                if len(updated) > 0:
                    total = total + len(updated)
                    logger.info(f'{len(updated)} updated work_items')
                    updated_message = WorkItemsUpdated(send=dict(
                        organization_key=message['organization_key'],
                        work_items_source_key=message['work_items_source_key'],
                        updated_work_items=updated
                    ))
                    self.publish(WorkItemsTopic, updated_message)
                    messages.append(updated_message)

            logger.info(f'{total} work items processed')
            return messages

        elif AtlassianConnectWorkItemEvent.message_type == message.message_type:
            return self.process_atlassian_connect_event(message)

        elif ConnectorEvent.message_type == message.message_type:
            for created, updated in self.process_connector_event(message):
                if len(created) > 0:
                    logger.info(f"{len(created)} work items sources created")

                if len(updated) > 0:
                    logger.info(f"{len(updated)} work items sources updated")

    def process_import_work_items(self, message):
        work_items_source_key = message['work_items_source_key']
        logger.info(f"Processing  {message.message_type}: "
                    f" Work Items Source Key : {work_items_source_key}")
        try:
            for work_items in commands.sync_work_items(self.consumer_context.token_provider, work_items_source_key):
                created = []
                updated = []
                for work_item in work_items:
                    if work_item['is_new']:
                        created.append(work_item)
                    else:
                        updated.append(work_item)

                yield created, updated

        except Exception as exc:
            raise_message_processing_error(message, 'Failed to sync work items', str(exc))

    def process_atlassian_connect_event(self, message):
        jira_connector_key = message['atlassian_connector_key']
        jira_event_type = message['atlassian_event_type']
        jira_event = json.loads(message['atlassian_event'])

        try:
            if jira_event_type in ['issue_created', 'issue_updated', 'issue_deleted']:
                work_item = jira_message_handler.handle_issue_events(jira_connector_key, jira_event_type, jira_event)
                if work_item:
                    if work_item.get('is_new'):
                        logger.info(f'new work_item created')
                        response_message = WorkItemsCreated(send=dict(
                            organization_key=work_item['organization_key'],
                            work_items_source_key=work_item['work_items_source_key'],
                            new_work_items=[work_item]
                        ))
                        self.publish(WorkItemsTopic, response_message)
                    else:
                        logger.info(f'new work_item updated')
                        response_message = WorkItemsUpdated(send=dict(
                            organization_key=work_item['organization_key'],
                            work_items_source_key=work_item['work_items_source_key'],
                            is_delete=work_item.get('is_delete') is not None,
                            updated_work_items=[work_item]
                        ))
                        self.publish(WorkItemsTopic, response_message)

                    return response_message

            elif jira_event_type in ['project_created', 'project_updated']:
                work_items_source = jira_message_handler.handle_project_events(jira_connector_key, jira_event_type, jira_event)
                if work_items_source:
                    if work_items_source[0].get('is_new'):
                        logger.info(f"new work_items source created {work_items_source.get('name')}")
                    else:
                        logger.info(f"work_items_source {work_items_source.get('name')} updated")

            else:
                raise ProcessingException(f"Cannot determine how to handle event_type {jira_event_type}")

        except Exception as exc:
            raise_message_processing_error(message, 'Failed to handle atlassian_connect_message', str(exc))

    @staticmethod
    def process_connector_event(message):
        connector_key = message['connector_key']
        event = message['event']
        connector_type = message['connector_type']
        product_type = message.get('product_type')

        logger.info(
            f"Processing  {message.message_type}: "
            f" Connector Key : {connector_key}"
            f" Event: {event}"
            f" Connector Type: {connector_type}"
            f" Product Type: {product_type}"
        )
        try:
            if event == 'enabled':
                for work_items_sources in commands.sync_work_items_sources(
                        connector_key=connector_key
                ):
                    created = []
                    updated = []
                    for work_items_source in work_items_sources:
                        if work_items_source['is_new']:
                            created.append(work_items_source)
                        else:
                            updated.append(work_items_source)

                    yield created, updated

        except Exception as exc:
            raise_message_processing_error(message, 'Failed to sync work items', str(exc))


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
