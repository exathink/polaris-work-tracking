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


def handle_card_event(connector_key, payload, channel=None):
    event = json.loads(payload)
    board_source_id = str(event['model']['id'])
    with db.orm_session() as session:
        work_items_source = WorkItemsSource.find_by_connector_key_and_source_id(
            session,
            connector_key=connector_key,
            source_id=board_source_id
        )
        if work_items_source:
            connector = connector_factory.get_connector(
                connector_key=work_items_source.connector_key,
                join_this=session
            )
            if connector:
                trello_board = TrelloBoard(token_provider=None, work_items_source=work_items_source,
                                           connector=connector)
                card_data = event['action']['data']['card']
                list_data = event['action']['data']['list']
                card_object = dict(
                    id=card_data.get('id'),
                    name=card_data.get('name'),
                    desc=card_data.get('desc') or '',
                    idShort=card_data.get('idShort'),
                    shortLink=card_data.get('shortLink'),
                    idList=list_data.get('id'),
                    idLabels=card_data.get('idLabels') or [],
                    shortUrl=card_data.get('shortUrl') or f'https://trello.com/c/{card_data.get("idShort")}'
                )
                work_items_source_data = trello_board.before_work_item_sync()
                work_items_source.update(work_items_source_data)
                session.flush()

                issue_data = trello_board.map_card_to_work_item(card_object)

                synced_issues = api.sync_work_items(work_items_source.key, [issue_data], join_this=session)
                if len(synced_issues) > 0:
                    if synced_issues[0]['is_new']:
                        publish.work_item_created_event(
                            organization_key=work_items_source.organization_key,
                            work_items_source_key=work_items_source.key,
                            new_work_items=synced_issues
                        )
                    else:
                        publish.work_item_updated_event(
                            organization_key=work_items_source.organization_key,
                            work_items_source_key=work_items_source.key,
                            updated_work_items=synced_issues
                        )
                return synced_issues


def handle_trello_event(connector_key, event_type, payload, channel=None):
    if event_type in ['createCard', 'updateCard']:
        return handle_card_event(connector_key, payload, channel)
