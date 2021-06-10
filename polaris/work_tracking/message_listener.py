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
from polaris.messaging.messages import ImportWorkItems, ImportWorkItem, WorkItemsCreated, WorkItemsUpdated, \
    WorkItemsSourceCreated, WorkItemsSourceUpdated, ProjectImported, ConnectorCreated, ConnectorEvent

from polaris.work_tracking.messages import AtlassianConnectWorkItemEvent, RefreshConnectorProjects, \
    ResolveWorkItemsForEpic, GitlabProjectEvent, TrelloBoardEvent

from polaris.messaging.topics import WorkItemsTopic, ConnectorsTopic, TopicSubscriber
from polaris.messaging.utils import raise_message_processing_error
from polaris.utils.config import get_config_provider
from polaris.utils.exceptions import ProcessingException
from polaris.utils.logging import config_logging
from polaris.utils.token_provider import get_token_provider
from polaris.work_tracking import commands
from polaris.work_tracking.integrations.atlassian import jira_message_handler
from polaris.work_tracking.integrations.gitlab import gitlab_message_handler
from polaris.work_tracking.integrations.trello import trello_message_handler

from polaris.common.enums import ConnectorType, ConnectorProductType

logger = logging.getLogger('polaris.work_tracking.message_listener')


# -------------------------------------------------
#
# ------------------------------------------------


def is_work_tracking_connector(connector_type, product_type):
    return connector_type in [
        ConnectorType.pivotal.value,
        ConnectorType.github.value,
        ConnectorType.gitlab.value,
    ] or product_type in [
               ConnectorProductType.jira.value
           ]


class WorkItemsTopicSubscriber(TopicSubscriber):
    def __init__(self, channel, publisher=None):
        super().__init__(
            topic=WorkItemsTopic(channel, create=True),
            subscriber_queue='work_items_work_items',
            message_classes=[
                # Events
                AtlassianConnectWorkItemEvent,
                ProjectImported,
                WorkItemsCreated,
                WorkItemsUpdated,
                GitlabProjectEvent,
                TrelloBoardEvent,
                # Commands
                ImportWorkItem,
                ImportWorkItems,
                ResolveWorkItemsForEpic
            ],
            publisher=publisher,
            exclusive=False
        )

    def dispatch(self, channel, message):

        if ProjectImported.message_type == message.message_type:
            project_summary = message['project_summary']
            import_messages = []
            for work_items_source in project_summary['work_items_sources']:
                import_work_items = ImportWorkItems(send=dict(
                    organization_key=message['organization_key'],
                    work_items_source_key=work_items_source['key']
                ))
                self.publish(WorkItemsTopic, import_work_items, channel=channel)
                import_messages.append(import_work_items)

            return import_messages

        elif ImportWorkItem.message_type == message.message_type:
            work_item = self.process_import_work_item(message)[0]
            if work_item.get('is_new') == True:
                created_message = WorkItemsCreated(send=dict(
                    organization_key=message['organization_key'],
                    work_items_source_key=message['work_items_source_key'],
                    new_work_items=[work_item]
                ))
                self.publish(WorkItemsTopic, created_message, channel=channel)
                return [created_message]
            else:
                updated_message = WorkItemsUpdated(send=dict(
                    organization_key=message['organization_key'],
                    work_items_source_key=message['work_items_source_key'],
                    updated_work_items=[work_item]
                ))
                self.publish(WorkItemsTopic, updated_message, channel=channel)
                return [updated_message]

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
                    self.publish(WorkItemsTopic, created_message, channel=channel)
                    messages.append(created_message)

                if len(updated) > 0:
                    total = total + len(updated)
                    logger.info(f'{len(updated)} updated work_items')
                    updated_message = WorkItemsUpdated(send=dict(
                        organization_key=message['organization_key'],
                        work_items_source_key=message['work_items_source_key'],
                        updated_work_items=updated
                    ))
                    self.publish(WorkItemsTopic, updated_message, channel=channel)
                    messages.append(updated_message)

            logger.info(f'{total} work items processed')
            return messages

        elif AtlassianConnectWorkItemEvent.message_type == message.message_type:
            return self.process_atlassian_connect_event(message)

        elif GitlabProjectEvent.message_type == message.message_type:
            return self.process_gitlab_project_event(message)

        elif TrelloBoardEvent.message_type == message.message_type:
            return self.process_trello_board_event(message)

        elif WorkItemsCreated.message_type == message.message_type:
            return self.process_work_items_created(message)

        elif WorkItemsUpdated.message_type == message.message_type:
            return self.process_work_items_updated(message)

        elif ResolveWorkItemsForEpic.message_type == message.message_type:
            total = 0
            messages = []
            for created, updated in self.process_resolve_work_items_for_epic(message):
                if len(created) > 0:
                    total = total + len(created)
                    logger.info(f'{len(created)} new work_items')
                    created_message = WorkItemsCreated(send=dict(
                        organization_key=message['organization_key'],
                        work_items_source_key=message['work_items_source_key'],
                        new_work_items=created
                    ))
                    self.publish(WorkItemsTopic, created_message, channel=channel)
                    messages.append(created_message)

                if len(updated) > 0:
                    total = total + len(updated)
                    logger.info(f'{len(updated)} updated work_items')
                    updated_message = WorkItemsUpdated(send=dict(
                        organization_key=message['organization_key'],
                        work_items_source_key=message['work_items_source_key'],
                        updated_work_items=updated
                    ))
                    self.publish(WorkItemsTopic, updated_message, channel=channel)
                    messages.append(updated_message)

            logger.info(f'{total} work items processed')
            return messages

    def process_import_work_item(self, message):
        work_items_source_key = message['work_items_source_key']
        logger.info(f"Processing  {message.message_type}: "
                    f" Work Items Source Key : {work_items_source_key}")
        try:
            work_item = [wi for wi in
                         commands.sync_work_item(self.consumer_context.token_provider, work_items_source_key,
                                                 message['source_id'])]
            return work_item
        except Exception as exc:
            raise_message_processing_error(message, 'Failed to sync work item', str(exc))

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
                    response_message = None
                    if work_item.get('is_new'):
                        logger.info(f'new work_item created')
                        response_message = WorkItemsCreated(send=dict(
                            organization_key=work_item['organization_key'],
                            work_items_source_key=work_item['work_items_source_key'],
                            new_work_items=[work_item]
                        ))
                        self.publish(WorkItemsTopic, response_message)
                    elif work_item.get('is_updated') or work_item.get('is_delete'):
                        logger.info(f'new work_item updated')
                        response_message = WorkItemsUpdated(send=dict(
                            organization_key=work_item['organization_key'],
                            work_items_source_key=work_item['work_items_source_key'],
                            is_delete=work_item.get('is_delete') is not None,
                            updated_work_items=[work_item]
                        ))
                        self.publish(WorkItemsTopic, response_message)

                    return response_message

            elif jira_event_type in ['issue_moved']:
                work_item_deleted, work_item_created = jira_message_handler.handle_issue_moved_event(jira_connector_key, jira_event_type, jira_event)

            elif jira_event_type in ['project_created', 'project_updated']:
                work_items_source = jira_message_handler.handle_project_events(jira_connector_key, jira_event_type,
                                                                               jira_event)
                if work_items_source:
                    if work_items_source[0].get('is_new'):
                        logger.info(f"new work_items source created {work_items_source.get('name')}")
                    else:
                        logger.info(f"work_items_source {work_items_source.get('name')} updated")

            else:
                raise ProcessingException(f"Cannot determine how to handle event_type {jira_event_type}")

        except Exception as exc:
            raise_message_processing_error(message, 'Failed to handle atlassian_connect_message', str(exc))

    def process_gitlab_project_event(self, message):
        connector_key = message['connector_key']
        event_type = message['event_type']
        payload = message['payload']

        logger.info(
            f"Processing  gitlab event {message.message_type}: "
        )
        try:
            return gitlab_message_handler.handle_gitlab_event(
                connector_key,
                event_type,
                payload
            )
        except Exception as exc:
            raise_message_processing_error(message, 'Failed to process gitlab repository event', str(exc))

    def process_trello_board_event(self, message):
        connector_key = message['connector_key']
        event_type = message['event_type']
        payload = message['payload']

        logger.info(
            f"Processing  trello board event {message.message_type}: "
        )
        try:
            return trello_message_handler.handle_trello_event(
                connector_key,
                event_type,
                payload
            )
        except Exception as exc:
            raise_message_processing_error(message, 'Failed to process trello board event', str(exc))

    def process_work_items_created(self, message):
        response_messages = []
        epics_imported = set()
        epics_to_import = set()
        for work_item in message['new_work_items']:
            if work_item['is_epic']:
                epics_imported.add(work_item.get('display_id'))
                response_message = ResolveWorkItemsForEpic(
                    send=dict(
                        organization_key=message['organization_key'],
                        work_items_source_key=message['work_items_source_key'],
                        epic=work_item
                    ))
                self.publish(WorkItemsTopic, response_message)
                response_messages.append(response_message)
            if work_item.get('parent_source_display_id') is not None and work_item.get('parent_key') is None:
                epics_to_import.add(work_item.get('parent_source_display_id'))

        for work_item_id in epics_to_import - epics_imported:
            response_message = ImportWorkItem(
                send=dict(
                    organization_key=message['organization_key'],
                    work_items_source_key=message['work_items_source_key'],
                    source_id=work_item_id
                )
            )
            self.publish(WorkItemsTopic, response_message)
            response_messages.append(response_message)
        return response_messages

    def process_work_items_updated(self, message):
        response_messages = []
        epics_imported = set()
        epics_to_import = set()
        for work_item in message['updated_work_items']:
            if work_item['is_epic']:
                epics_imported.add(work_item.get('display_id'))
                response_message = ResolveWorkItemsForEpic(
                    send=dict(
                        organization_key=message['organization_key'],
                        work_items_source_key=message['work_items_source_key'],
                        epic=work_item
                    ))
                self.publish(WorkItemsTopic, response_message)
                response_messages.append(response_message)
            if work_item.get('parent_source_display_id') is not None and work_item.get('parent_key') is None:
                epics_to_import.add(work_item.get('parent_source_display_id'))

        for work_item_id in epics_to_import - epics_imported:
            response_message = ImportWorkItem(
                send=dict(
                    organization_key=message['organization_key'],
                    work_items_source_key=message['work_items_source_key'],
                    source_id=work_item_id
                )
            )
            self.publish(WorkItemsTopic, response_message)
            response_messages.append(response_message)
        return response_messages

    def process_resolve_work_items_for_epic(self, message):
        work_items_source_key = message['work_items_source_key']
        logger.info(f"Processing  {message.message_type}: "
                    f" Work Items Source Key : {work_items_source_key}")
        try:
            for work_items in commands.sync_work_items_for_epic(work_items_source_key, message['epic']):
                created = []
                updated = []
                for work_item in work_items:
                    if work_item['is_new']:
                        created.append(work_item)
                    else:
                        updated.append(work_item)

                yield created, updated

        except Exception as exc:
            raise_message_processing_error(message, 'Failed to resolve work items for epic', str(exc))


class ConnectorsTopicSubscriber(TopicSubscriber):
    def __init__(self, channel, publisher=None):
        super().__init__(
            topic=ConnectorsTopic(channel, create=True),
            subscriber_queue='connectors_work_items',
            message_classes=[
                # Events
                ConnectorCreated,
                ConnectorEvent,

                # Commands
                RefreshConnectorProjects
            ],
            publisher=publisher,
            exclusive=False
        )

    def dispatch(self, channel, message):

        if ConnectorCreated.message_type == message.message_type:
            created_messages = []
            updated_messages = []
            for created, updated in self.process_connector_created(message):
                self.publish_responses(created, created_messages, updated, updated_messages)

            return created_messages, updated_messages

        elif RefreshConnectorProjects.message_type == message.message_type:
            created_messages = []
            updated_messages = []

            for created, updated in self.process_refresh_connector_projects(message):
                self.publish_responses(created, created_messages, updated, updated_messages)

            return created_messages, updated_messages

        elif ConnectorEvent.message_type == message.message_type:
            created_messages = []
            updated_messages = []
            for created, updated in self.process_connector_event(message):
                self.publish_responses(created, created_messages, updated, updated_messages)

            return created_messages, updated_messages

    def publish_responses(self, created, created_messages, updated, updated_messages):
        if len(created) > 0:
            logger.info(f"{len(updated)} work items sources updated")
            for work_items_source in created:
                created_message = WorkItemsSourceCreated(
                    send=dict(
                        work_items_source=work_items_source
                    )
                )
                self.publish(WorkItemsTopic, created_message)
                created_messages.append(created_message)
        if len(updated) > 0:
            logger.info(f"{len(updated)} work items sources updated")
            for work_items_source in updated:
                updated_message = WorkItemsSourceUpdated(
                    send=dict(
                        work_items_source=work_items_source
                    )
                )
                self.publish(WorkItemsTopic, updated_message)
                updated_messages.append(updated_message)

    @staticmethod
    def process_connector_created(message):
        connector_key = message['connector_key']
        connector_type = message['connector_type']
        product_type = message.get('product_type')
        if is_work_tracking_connector(connector_type, product_type):
            logger.info(
                f"Processing  {message.message_type}: "
                f" Connector Key : {connector_key}"
                f" Connector Type: {connector_type}"
                f" Product Type: {product_type}"
            )
            try:
                if connector_type in ['pivotal', 'github', 'gitlab']:
                    yield from ConnectorsTopicSubscriber.sync_work_items_sources(connector_key)
            except Exception as exc:
                raise_message_processing_error(message, 'Failed to sync work items sources', str(exc))

    @staticmethod
    def process_connector_event(message):
        connector_key = message['connector_key']
        event = message['event']
        connector_type = message['connector_type']
        product_type = message.get('product_type')
        if is_work_tracking_connector(connector_type, product_type):
            logger.info(
                f"Processing  {message.message_type}: "
                f" Connector Key : {connector_key}"
                f" Event: {event}"
                f" Connector Type: {connector_type}"
                f" Product Type: {product_type}"
            )
            try:
                if event == 'enabled':
                    yield from ConnectorsTopicSubscriber.sync_work_items_sources(connector_key)
            except Exception as exc:
                raise_message_processing_error(message, 'Failed to sync work items', str(exc))

    @staticmethod
    def process_refresh_connector_projects(message):
        connector_key = message['connector_key']
        tracking_receipt_key = message.get('tracking_receipt_key')
        logger.info(
            f"Processing  {message.message_type}: "
            f" Connector Key : {connector_key}"

        )
        try:
            yield from ConnectorsTopicSubscriber.sync_work_items_sources(connector_key,
                                                                         tracking_receipt_key=tracking_receipt_key)
        except Exception as exc:
            raise_message_processing_error(message, 'Failed to sync work items sources', str(exc))

    @staticmethod
    def sync_work_items_sources(connector_key, tracking_receipt_key=None):
        for work_items_sources in commands.sync_work_items_sources(
                connector_key=connector_key,
                tracking_receipt_key=tracking_receipt_key
        ):
            created = []
            updated = []
            for work_items_source in work_items_sources:
                if work_items_source['is_new']:
                    created.append(work_items_source)
                else:
                    updated.append(work_items_source)

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
            WorkItemsTopicSubscriber,
            ConnectorsTopicSubscriber
        ],
        token_provider=token_provider
    ).start_consuming()
