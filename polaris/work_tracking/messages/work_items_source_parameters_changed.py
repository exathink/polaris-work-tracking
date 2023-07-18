# -*- coding: utf-8 -*-

#  Copyright (c) Exathink, LLC  2016-2023.
#  All rights reserved
#

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from marshmallow import fields

from polaris.messaging.messages import Message


class ParentPathSelectorsChanged(Message):
    message_type = 'work_items_sources.parent_path_selectors_changed'

    organization_key = fields.String(required=True)
    work_items_source_key = fields.String(required=True)


class CustomTagMappingChanged(Message):
    message_type = 'work_items_sources.custom_tag_mapping_changed'

    organization_key = fields.String(required=True)
    work_items_source_key = fields.String(required=True)