# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from datetime import datetime

from polaris.common import db
from polaris.utils.exceptions import ProcessingException
from polaris.work_tracking import connector_factory
from polaris.work_tracking.db import api
from polaris.work_tracking.db.model import WorkItemsSource
from polaris.work_tracking.integrations.atlassian.jira_work_items_source import JiraProject
from polaris.common.enums import WorkItemsSourceImportState


def handle_issue_moved_event(jira_connector_key, jira_event):
    issue = jira_event.get('issue')
    if issue:
        changelog = jira_event.get('changelog')
        for item in changelog.get('items'):
            if item['field'] == 'project':
                source_project_id = item['from']
                target_project_id = item['to']
        with db.orm_session() as session:
            source_work_items_source = WorkItemsSource.find_by_connector_key_and_source_id(
                session,
                connector_key=jira_connector_key,
                source_id=source_project_id
            )
            target_work_items_source = WorkItemsSource.find_by_connector_key_and_source_id(
                session,
                connector_key=jira_connector_key,
                source_id=target_project_id
            )
            if source_work_items_source:
                if target_work_items_source:
                    if target_work_items_source.import_state == WorkItemsSourceImportState.auto_update.value:
                        target_jira_project_source = JiraProject(target_work_items_source)
                        moved_work_item_data = target_jira_project_source.map_issue_to_work_item_data(issue)
                        moved_work_item = api.move_work_item(source_work_items_source.key, target_work_items_source.key,
                                                             moved_work_item_data,
                                                             join_this=session)
                        moved_work_item['organization_key'] = target_work_items_source.organization_key
                        moved_work_item['source_work_items_source_key'] = source_work_items_source.key
                        moved_work_item['target_work_items_source_key'] = target_work_items_source.key
                        return dict(is_moved=True, is_new=False, work_item_data=moved_work_item)
                    else:
                        # Target work items source is present but not yet active.
                        # So we can possibly link the work item to this work items source,
                        # but it stays suppressed unless the work items source import state auto_update is set to True.
                        # This case can possibly be handled within api.move_work_item
                        return dict(is_moved=False)
                else:
                    # Target work items source is not present.
                    # So we can update the work item state as moved to this work items source / project.
                    # This case can possibly be handled within api.move_work_item
                    return dict(is_moved=False)
            else:
                if target_work_items_source:
                    if target_work_items_source.import_state == WorkItemsSourceImportState.auto_update.value:
                        target_jira_project_source = JiraProject(target_work_items_source)
                        new_work_item_data = target_jira_project_source.map_issue_to_work_item_data(issue)
                        new_work_item = api.import_work_item(target_work_items_source.key, new_work_item_data,
                                                             join_this=session)
                        new_work_item['organization_key'] = target_work_items_source.organization_key
                        new_work_item['work_items_source_key'] = target_work_items_source.key
                        return dict(is_new=True, is_moved=True, work_item_data=new_work_item)
                    else:
                        # Target work items source is present but not yet active.
                        # So we can update the work item state as moved to this work items source / project
                        # Need to do some separate handling for this case, may be by importing the work item as new,
                        # but it stays suppressed unless the work items source import state auto_update is set to True
                        return dict(is_moved=False)
                else:
                    # Target and source not present, we do nothing
                    return dict(is_moved=False)
    else:
        raise ProcessingException(f"Could not find issue field on jira issue event {jira_event}. ")


def handle_issue_events(jira_connector_key, jira_event_type, jira_event):
    issue = jira_event.get('issue')
    if issue:
        if jira_event.get('issue_event_type_name') == 'issue_moved':
            return handle_issue_moved_event(jira_connector_key, jira_event)
        else:
            project_id = issue['fields']['project']['id']
            with db.orm_session() as session:
                work_items_source = WorkItemsSource.find_by_connector_key_and_source_id(
                    session,
                    connector_key=jira_connector_key,
                    source_id=project_id
                )
                if work_items_source and work_items_source.import_state == WorkItemsSourceImportState.auto_update.value:
                    # if the work_items source is not enabled for updates nothing is propagated
                    # This ensures that even though the connector is active, it wont import issues etc until
                    # the work_items_source is associated with a project and an initial import is done.
                    jira_project_source = JiraProject(work_items_source)
                    work_item_data = jira_project_source.map_issue_to_work_item_data(issue)
                    if work_item_data:
                        work_item = {}
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
        raise ProcessingException(f"Could not find issue field on jira issue event {jira_event}. ")


def handle_project_events(jira_connector_key, jira_event_type, jira_event):
    project = jira_event.get('project')
    if project is not None and jira_event_type in ['project_created', 'project_updated']:
        project_id = project.get('id')
        jira_connector = connector_factory.get_connector(connector_key=jira_connector_key)
        with db.orm_session() as session:
            work_items_source_data = jira_connector.fetch_work_items_source_data_for_project(project_id)
            if work_items_source_data is not None:
                return api.sync_work_items_sources(jira_connector, [work_items_source_data], join_this=session)


    else:
        raise ProcessingException(
            f'Did not find a project entry in project event: '
            f'Connector {jira_connector_key}'
            f'Event: {jira_event}'

        )
