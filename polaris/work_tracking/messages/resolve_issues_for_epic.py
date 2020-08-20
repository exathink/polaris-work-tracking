# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal


from marshmallow import fields

from polaris.messaging.messages import Message


class ResolveIssuesForEpic(Message):
    message_type = 'work_items.resolve_issues_for_epic'

    organization_key = fields.String(required=True)
    work_items_source_key = fields.String(required=True)
    epic_id = fields.String(required=True)
