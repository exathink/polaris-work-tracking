# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2019) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from polaris.messaging.messages import register_messages
from .atlassian_connect_work_item_event import AtlassianConnectWorkItemEvent
from .refresh_connector_projects import RefreshConnectorProjects
from .resolve_issues_for_epic import ResolveIssuesForEpic

# Add this to the global message factory so that the messages can be desrialized on reciept.
register_messages([
    AtlassianConnectWorkItemEvent,
    RefreshConnectorProjects,
    ResolveIssuesForEpic,
])

