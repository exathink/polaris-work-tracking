# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal

import json

from polaris.work_tracking import publish
from polaris.common import db
from polaris.work_tracking import connector_factory
from polaris.work_tracking.db import api
from polaris.work_tracking.integrations.trello import TrelloBoard
from polaris.work_tracking.db.model import WorkItemsSource


def handle_create_card_event(connector_key, payload, channel=None):
    pass


def handle_update_card_event(connector_key, payload, channel=None):
    pass


def handle_trello_event(connector_key, event_type, payload, channel=None):
    if event_type == 'createCard':
        return handle_create_card_event(connector_key, payload, channel)
    if event_type == 'updateCard':
        return handle_update_card_event(connector_key, payload, channel)


