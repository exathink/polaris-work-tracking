# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal

import logging
import requests

from polaris.integrations.trello import TrelloConnector
from polaris.utils.config import get_config_provider
from polaris.utils.exceptions import ProcessingException


config_provider = get_config_provider()

logger = logging.getLogger('polaris.work_tracking.trello')


class TrelloWorkTrackingConnector(TrelloConnector):

    def __init__(self, connector):
        super().__init__(connector)

    def fetch_trello_boards(self):
        fetch_boards_url = f'{self.base_url}/members/me/boards'
        while fetch_boards_url is not None:
            response = requests.get(
                fetch_boards_url,
                headers={'Authorization': f'OAuth oauth_consumer_key="{self.api_key}", oauth_token="{self.access_token}"'}
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
        pass
