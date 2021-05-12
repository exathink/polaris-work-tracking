# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal


from marshmallow import fields

from polaris.messaging.messages import Message


class TrelloBoardEvent(Message):
    message_type = 'work_tracking.trello_board_event'

    connector_key = fields.String(required=True)
    event_type = fields.String(required=True)

    payload = fields.String(required=True)
