# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from marshmallow import fields

from polaris.messaging.messages import Message


class ConnectorEvent(Message):
    message_type = 'work_items.connector_event'

    connector_key = fields.String(required=True)
    connector_type = fields.String(required=True)
    product_type = fields.String(required=False)

    event = fields.String(required=True)

