# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal


import pytz
import logging
import requests
from enum import Enum
from datetime import datetime

from polaris.integrations.trello import TrelloConnector
from polaris.utils.config import get_config_provider
from polaris.utils.exceptions import ProcessingException
from polaris.work_tracking import connector_factory
from polaris.common.enums import WorkTrackingIntegrationType
from polaris.utils.collections import find
from polaris.common.enums import TrelloWorkItemType

config_provider = get_config_provider()

logger = logging.getLogger('polaris.work_tracking.trello')


class TrelloWorkTrackingConnector(TrelloConnector):

    def __init__(self, connector):
        super().__init__(connector)

    def map_project_to_work_items_sources_data(self, project):
        return dict(
            integration_type=WorkTrackingIntegrationType.trello.value,
            work_items_source_type=TrelloWorkItemSourceType.projects.value,
            parameters=dict(),
            commit_mapping_scope='organization',
            source_id=project['id'],
            name=project['name'],
            url=project['url'],
            description=project['desc'],
            custom_fields=[]
        )

    def fetch_trello_boards(self):
        fetch_boards_url = f'{self.base_url}/members/me/boards'
        while fetch_boards_url is not None:
            response = requests.get(
                fetch_boards_url,
                headers={
                    'Authorization': f'OAuth oauth_consumer_key="{self.api_key}", oauth_token="{self.access_token}"'}
            )
            if response.ok:
                yield response.json()
                if 'next' in response.links:
                    fetch_boards_url = response.links['next']['url']
                else:
                    fetch_boards_url = None
            else:
                raise ProcessingException(
                    f"Trello Boards fetch failed {response.text} status: {response.status_code}\n"
                )

    def fetch_work_items_sources_to_sync(self):
        for boards in self.fetch_trello_boards():
            yield [
                self.map_project_to_work_items_sources_data(board)
                for board in boards
            ]

    def register_project_webhooks(self, project_source_id, registered_webhooks):
        deleted_hook_ids = []
        for inactive_hook_id in registered_webhooks:
            if self.delete_project_webhook(inactive_hook_id):
                logger.info(f"Deleted webhook with id {inactive_hook_id} for repo {project_source_id}")
                deleted_hook_ids.append(inactive_hook_id)
            else:
                logger.info(f"Webhook with id {inactive_hook_id} for project {project_source_id} could not be deleted")

        # Register new webhook now
        callback_url = f"{config_provider.get('TRELLO_WEBHOOKS_BASE_URL')}" \
                       f"/project/webhooks/{self.key}/"

        add_hook_url = f"{self.base_url}/webhooks/"
        params = dict(
            key=self.api_key,
            token=self.access_token,
            callbackURL=callback_url,
            idModel=project_source_id
        )

        response = requests.post(
            add_hook_url,
            headers={"Accept": "application/json"},
            params=params
        )
        if response.ok:
            result = response.json()
            active_hook_id = result['id']
        else:
            raise ProcessingException(
                f"Webhook registration failed due to status:{response.status_code} message:{response.text}")
        return dict(
            success=True,
            active_webhook=active_hook_id,
            deleted_webhooks=deleted_hook_ids,
            registered_events=[],
        )

    def delete_project_webhook(self, inactive_hook_id):
        delete_hook_url = f"{self.base_url}/webhooks/{inactive_hook_id}"
        params = dict(
            key=self.api_key,
            token=self.access_token
        )
        response = requests.post(
            delete_hook_url,
            headers={"Accept": "application/json"},
            params=params
        )
        if response.ok:
            return True


class TrelloWorkItemSourceType(Enum):
    projects = 'boards'


class TrelloCardsWorkItemsSource:

    @staticmethod
    def create(token_provider, work_items_source):
        if work_items_source.work_items_source_type == TrelloWorkItemSourceType.projects.value:
            return TrelloBoard(token_provider, work_items_source)
        else:
            raise ProcessingException(f"Unknown work items source type {work_items_source.work_items_source_type}")


class TrelloBoard(TrelloCardsWorkItemsSource):

    def __init__(self, token_provider, work_items_source, connector=None):
        self.work_items_source = work_items_source
        self.last_updated = work_items_source.latest_work_item_update_timestamp
        self.board_lists = work_items_source.source_data.get(
            'board_lists') if work_items_source.source_data.get('board_lists') is not None else []
        self.board_labels = work_items_source.source_data.get(
            'board_labels') if work_items_source.source_data.get('board_labels') is not None else []
        self.source_states = work_items_source.source_states
        self.trello_connector = connector if connector else connector_factory.get_connector(
            connector_key=self.work_items_source.connector_key
        )
        self.source_project_id = work_items_source.source_id
        self.api_key = self.trello_connector.api_key
        self.access_token = self.trello_connector.access_token

    def resolve_work_item_type_for_card(self, labels):
        lower_case_labels = [label.lower() for label in labels]
        for label in lower_case_labels:
            if label == 'story':
                return TrelloWorkItemType.story.value
            if label == 'feature':
                return TrelloWorkItemType.feature.value
            if label == 'enhancement':
                return TrelloWorkItemType.enhancement.value
            if label == 'bug' or label == 'defect':
                return TrelloWorkItemType.bug.value
            if label == 'task':
                return TrelloWorkItemType.task.value
        return TrelloWorkItemType.issue.value

    def map_card_to_work_item(self, card):

        def get_created_date(card_id):
            creation_time = datetime.fromtimestamp(int(card_id[0:8], 16))
            utc_creation_time = pytz.utc.localize(creation_time)
            return utc_creation_time

        board_list = find(self.board_lists, lambda board_list: board_list['id'] == card['idList'])
        card_labels = []
        for label_id in card.get('idLabels'):
            card_label = find(self.board_labels, lambda board_label: board_label['id'] == label_id)
            if card_label and card_label.get('name'):
                card_labels.append(card_label['name'])
        work_item_type = self.resolve_work_item_type_for_card(card_labels)

        return dict(
            name=card.get('name')[:255],
            description=card.get('desc') or '',
            is_bug=work_item_type == TrelloWorkItemType.bug.value,
            tags=card_labels,
            source_id=str(card.get('id')),
            source_last_updated=card.get('dateLastActivity') or get_created_date(card.get('id')),
            source_created_at=get_created_date(card.get('id')),
            source_display_id=str(card.get('idShort')),
            source_state=board_list.get('name'),
            is_epic=False,
            url=card.get('shortUrl'),
            work_item_type=work_item_type,
            api_payload=card,
            commit_identifiers=[str(card.get('idShort')), card.get('shortLink'),
                                card.get('shortUrl').replace('https://', '')]
        )

    def fetch_card(self, card_id):
        fetch_card_url = f'{self.trello_connector.base_url}/cards/{card_id}'
        response = requests.get(
            fetch_card_url,
            headers={
                'Authorization': f'OAuth oauth_consumer_key="{self.api_key}", oauth_token="{self.access_token}"'}
        )
        if response.ok:
            yield response.json()
        else:
            raise ProcessingException(
                f"Fetch from server failed {response.text} status: {response.status_code}\n"
            )

    def fetch_cards(self):
        query_params = dict(limit=100)
        fetch_cards_url = f'{self.trello_connector.base_url}/boards/{self.source_project_id}/cards'
        while fetch_cards_url is not None:
            response = requests.get(
                fetch_cards_url,
                params=query_params,
                headers={
                    'Authorization': f'OAuth oauth_consumer_key="{self.api_key}", oauth_token="{self.access_token}"'}
            )
            if response.ok:
                yield response.json()
                if 'next' in response.links:
                    fetch_cards_url = response.links['next']['url']
                else:
                    fetch_cards_url = None
            else:
                raise ProcessingException(
                    f"Fetch from server failed {response.text} status: {response.status_code}\n"
                )

    def fetch_work_items_to_sync(self):
        self.before_work_item_sync()
        for cards in self.fetch_cards():
            yield [
                self.map_card_to_work_item(card)
                for card in cards
            ]

    def fetch_board_lists(self):
        fetch_lists_url = f'{self.trello_connector.base_url}/boards/{self.source_project_id}/lists'
        while fetch_lists_url is not None:
            response = requests.get(
                fetch_lists_url,
                headers={
                    'Authorization': f'OAuth oauth_consumer_key="{self.api_key}", oauth_token="{self.access_token}"'}
            )
            if response.ok:
                yield response.json()
                if 'next' in response.links:
                    fetch_lists_url = response.links['next']['url']
                else:
                    fetch_lists_url = None
            else:
                raise ProcessingException(
                    f"Fetch from server failed {response.text} status: {response.status_code}\n"
                )

    def fetch_board_labels(self):
        fetch_labels_url = f'{self.trello_connector.base_url}/boards/{self.source_project_id}/labels'
        while fetch_labels_url is not None:
            response = requests.get(
                fetch_labels_url,
                headers={
                    'Authorization': f'OAuth oauth_consumer_key="{self.api_key}", oauth_token="{self.access_token}"'}
            )
            if response.ok:
                yield response.json()
                if 'next' in response.links:
                    fetch_labels_url = response.links['next']['url']
                else:
                    fetch_labels_url = None
            else:
                raise ProcessingException(
                    f"Fetch from server failed {response.text} status: {response.status_code}\n"
                )

    def before_work_item_sync(self):
        # Fetch board lists for state of card
        self.board_lists = [data for data in self.fetch_board_lists()][0]
        # Fetch board labels for type of card
        self.board_labels = [data for data in self.fetch_board_labels()][0]
        source_data = dict(board_lists=self.board_lists, board_labels=self.board_labels)
        source_states = []
        for board_list in self.board_lists:
            source_states.append(board_list['name'])
        self.source_states = source_states
        return dict(
            source_data=source_data,
            source_states=self.source_states
        )
