# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from enum import Enum
import json
import logging
from polaris.utils.exceptions import ProcessingException
from polaris.common.enums import JiraWorkItemType
from polaris.integrations.atlassian_connect import PolarisAtlassianConnector
from polaris.work_tracking.messages import AtlassianConnectWorkItemEvent
from polaris.work_tracking.db.model import WorkItemsSource

logger = logging.getLogger('polaris.work_tracking.jira')


class JiraWorkItemSourceType(Enum):
    project = 'project'


class JiraWorkItemsSource:

    @staticmethod
    def create(token_provider, work_items_source):
        if work_items_source.work_items_source_type == JiraWorkItemSourceType.project.value:
            return JiraProject(work_items_source)
        else:
            raise ProcessingException(f"Unknown work items source type {work_items_source.work_items_source_type}")


class JiraProject(JiraWorkItemsSource):

    def __init__(self, work_items_source):

        self.work_items_source = work_items_source
        self.project_id = work_items_source.parameters.get('project_id')
        self.initial_import_days = int(work_items_source.parameters.get('initial_import_days', 90))
        self.last_updated = work_items_source.latest_work_item_update_timestamp

        self.jira_connector = PolarisAtlassianConnector(
            self.work_items_source.parameters.get('jira_connector_key'))
        # map standard JIRA issue types to JiraWorkItemType enum values.
        self.work_item_type_map = dict(
            Story=JiraWorkItemType.story.value,
            Bug=JiraWorkItemType.bug.value,
            Epic=JiraWorkItemType.epic.value,
            Epic2=JiraWorkItemType.epic.value
        )

    def map_issue_to_work_item_data(self, issue):
        fields = issue.get('fields')
        issue_type = fields.get('issuetype').get('name')
        if issue_type in self.work_item_type_map:
            return(
                dict(
                    name=fields.get('summary'),
                    description=fields.get('description'),
                    is_bug=issue_type == 'Bug',
                    work_item_type=self.work_item_type_map.get(issue_type),
                    tags=[],
                    url=issue.get('self'),
                    source_id=str(issue.get('id')),
                    source_display_id=issue.get('key'),
                    source_last_updated=fields.get('updated'),
                    source_created_at=fields.get('created'),
                    source_state=fields.get('status').get('name')
                )
            )

    def fetch_work_items_to_sync(self):

        jql_base = f"project = {self.project_id} "

        if self.work_items_source.last_synced is None or self.last_updated is None:
            jql = f'{jql_base} AND created >= "-{self.initial_import_days}d"'
        else:
            jql = f'{jql_base} AND updated > "{self.last_updated.isoformat()}"'

        query_params = dict(
            fields="summary,created,updated, description,labels,issuetype,status",
            jql=jql,
            maxResults=100
        )

        response = self.jira_connector.get(
            self.jira_connector.api_url('/search'),
            headers={"Accept": "application/json"},
            params=query_params
        )
        if response.ok:
            offset = 0
            body = response.json()
            total = int(body.get('total') or 0)
            while offset < total and response.ok:
                issues = body.get('issues', [])
                if len(issues) == 0:
                    break
                work_items = []
                for issue in issues:
                    work_item_data = self.map_issue_to_work_item_data(issue)
                    if work_item_data:
                        work_items.append(work_item_data)

                yield work_items
                offset = offset + len(issues)
                query_params['startAt'] = offset
                response = self.jira_connector.get(
                    self.jira_connector.api_url('/search'),
                    headers={"Accept": "application/json"},
                    params=query_params
                )
                body = response.json()
