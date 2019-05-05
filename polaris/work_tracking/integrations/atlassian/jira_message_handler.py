# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import json
from datetime import datetime
from polaris.common import db
from polaris.work_tracking.db import api

from polaris.work_tracking.db.model import WorkItemsSource
from polaris.utils.exceptions import ProcessingException
from polaris.common.enums import WorkTrackingIntegrationType
from polaris.work_tracking.integrations.atlassian.jira_work_items_source import JiraProject


def handle_issue_events(jira_connector_key, jira_event_type, jira_event):
    issue = jira_event.get('issue')
    if issue:
        project_id = issue['fields']['project']['id']
        with db.orm_session() as session:
            work_items_sources = WorkItemsSource.find_by_integration_type_and_parameters(
                session,
                WorkTrackingIntegrationType.jira.value,
                jira_connector_key=jira_connector_key,
                project_id=project_id
            )
            if len(work_items_sources) > 0:
                if len(work_items_sources) == 1:
                    work_items_source = work_items_sources[0]
                    jira_project_source = JiraProject(work_items_source)
                    work_item_data = jira_project_source.map_issue_to_work_item_data(issue)
                    if work_item_data:
                        if jira_event_type == 'issue_created':
                            work_item = api.insert_work_item(work_items_source.key, work_item_data, join_this=session)
                        elif jira_event_type == 'issue_updated':
                            work_item = api.update_work_item(work_items_source.key, work_item_data, join_this=session)
                        elif jira_event_type == 'issue_deleted':
                            work_item_data['deleted_at'] = datetime.utcnow()
                            work_item = api.delete_work_item(work_items_source.key, work_item_data, join_this=session)


                        work_item['organization_key'] = work_items_source.organization_key
                        work_item['work_items_source_key'] = work_items_source.key
                        return work_item
                else:
                    raise ProcessingException(f"More than one work items source was f"
                                              f"ound with connector key {jira_connector_key} and project_id {project_id}")

    else:
        raise ProcessingException(f"Could not find issue field on jira issue event {jira_event}. ")
