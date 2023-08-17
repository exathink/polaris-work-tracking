# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2019) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from polaris.messaging.messages import register_messages
from .atlassian_connect_work_item_event import AtlassianConnectWorkItemEvent
from .refresh_connector_projects import RefreshConnectorProjects
from .resolve_work_items_for_epic import ResolveWorkItemsForEpic
from .gitlab_project_event import GitlabProjectEvent
from .trello_board_event import TrelloBoardEvent
from .work_items_source_parameters_changed import ParentPathSelectorsChanged, CustomTagMappingChanged
from .reprocess_work_items import ReprocessWorkItems

# Add this to the global message factory so that the messages can be deserialized on receipt.
register_messages([
    AtlassianConnectWorkItemEvent,
    RefreshConnectorProjects,
    ResolveWorkItemsForEpic,
    GitlabProjectEvent,
    TrelloBoardEvent,
    ParentPathSelectorsChanged,
    CustomTagMappingChanged,
    ReprocessWorkItems
])

