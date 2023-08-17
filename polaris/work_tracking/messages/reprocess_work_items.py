#  Copyright (c) Exathink, LCC 2023.
#  All rights reserved
#
from marshmallow import fields

from polaris.messaging.messages import Message

class ReprocessWorkItems(Message):
    message_type = 'work_items.reprocess_work_items'
    organization_key = fields.String(required=True)
    work_items_source_key = fields.String(required=True)
    attributes_to_check = fields.List(fields.String(),required=False, allow_none=True)