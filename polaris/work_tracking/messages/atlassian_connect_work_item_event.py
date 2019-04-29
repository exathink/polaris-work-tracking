# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar


from marshmallow import fields

from polaris.messaging.messages import Message


class AtlassianConnectWorkItemEventMessage(Message):
    message_type = 'work_items.atlassian_connect_event'

    atlassian_connector_key = fields.String(required=True)
    atlassian_event_type = fields.String(required=True)

    # the atlassian event is passed through as string and handled on the receiver end.
    atlassian_event = fields.String(required=True)
