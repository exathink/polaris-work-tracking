# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal

import logging
import requests
from enum import Enum

from polaris.integrations.trello import TrelloConnector
from polaris.utils.config import get_config_provider
from polaris.utils.exceptions import ProcessingException
from polaris.work_tracking import connector_factory
from polaris.common.enums import WorkTrackingIntegrationType

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


class TrelloWorkItemSourceType(Enum):
    projects = 'boards'


class TrelloCardsWorkItemsSource:

    @staticmethod
    def create(token_provider, work_items_source):
        if work_items_source.work_items_source_type == TrelloWorkItemSourceType:
            return TrelloBoard(token_provider, work_items_source)
        else:
            raise ProcessingException(f"Unknown work items source type {work_items_source.work_items_source_type}")


class TrelloBoard(TrelloCardsWorkItemsSource):

    def __init__(self, token_provider, work_items_source, connector=None):
        self.work_items_source = work_items_source
        self.last_updated = work_items_source.latest_work_item_update_timestamp
        self.source_states = work_items_source.source_states
        self.trello_connector = connector if connector else connector_factory.get_connector(
            connector_key=self.work_items_source.connector_key
        )
        self.source_project_id = work_items_source.source_id
        self.api_key = self.trello_connector.api_key
        self.access_token = self.trello_connector.access_token


    def map_card_to_work_item(self, card):
        return dict()

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
        for cards in self.fetch_cards():
            yield [
                self.map_card_to_work_item(card)
                for card in cards
            ]