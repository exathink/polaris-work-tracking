#  Copyright (c) Exathink, LCC 2023.
#  All rights reserved
#
from marshmallow import fields

from polaris.messaging.messages import Command

class ReprocessWorkItems(Command):
    message_type = 'commands.reprocess_work_items'
    organization_key = fields.String(required=True)
    work_items_source_key = fields.String(required=True)
    attributes_to_check = fields.List(fields.String(),required=False, allow_none=True)