# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging
from datetime import datetime

import polaris.work_tracking.connector_factory
from polaris.common.enums import JiraWorkItemType, JiraWorkItemSourceType
from polaris.utils.exceptions import ProcessingException

logger = logging.getLogger('polaris.work_tracking.jira')





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
        self.project_id = work_items_source.source_id
        self.initial_import_days = int(self.work_items_source.parameters.get('initial_import_days', 90))
        self.last_updated = work_items_source.latest_work_item_update_timestamp

        self.jira_connector = polaris.work_tracking.connector_factory.get_connector(
            connector_key=self.work_items_source.connector_key
        )
        # map standard JIRA issue types to JiraWorkItemType enum values.
        self.work_item_type_map = dict(
            Story=JiraWorkItemType.story.value,
            Bug=JiraWorkItemType.bug.value,
            Epic=JiraWorkItemType.epic.value,
            Epic2=JiraWorkItemType.epic.value
        )

    @staticmethod
    def jira_time_to_utc_time_string(jira_time_string):
        try:
            return datetime.strftime(
                datetime.fromtimestamp(datetime.strptime(jira_time_string,"%Y-%m-%dT%H:%M:%S.%f%z").timestamp()),
                "%Y-%m-%dT%H:%M:%S.%f%z"
            )
        except ValueError as exc:
            logger.warning(f"Jira timestamp {jira_time_string} "
                           f"could not be parsed to UTC returning the original string instead.")
            return jira_time_string


    def map_issue_to_work_item_data(self, issue):
        fields = issue.get('fields')
        issue_type = fields.get('issuetype').get('name')

        return (
            dict(
                name=fields.get('summary'),
                description=fields.get('description'),
                is_bug=issue_type == 'Bug',
                work_item_type=self.work_item_type_map.get(issue_type, JiraWorkItemType.story.value),
                tags=[],
                url=issue.get('self'),
                source_id=str(issue.get('id')),
                source_display_id=issue.get('key'),
                source_last_updated=self.jira_time_to_utc_time_string(fields.get('updated')),
                source_created_at=self.jira_time_to_utc_time_string(fields.get('created')),
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
            '/search',
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
                    '/search',
                    headers={"Accept": "application/json"},
                    params=query_params
                )
                body = response.json()
