# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging
from datetime import datetime, timedelta
from polaris.utils.collections import find

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
        self.last_updated_issue_source_id = work_items_source.most_recently_updated_work_item_source_id

        self.jira_connector = polaris.work_tracking.connector_factory.get_connector(
            connector_key=self.work_items_source.connector_key
        )
        # map standard JIRA issue types to JiraWorkItemType enum values.
        self.work_item_type_map = {
            'Story': JiraWorkItemType.story.value,
            'Bug': JiraWorkItemType.bug.value,
            'Epic': JiraWorkItemType.epic.value,
            'Task': JiraWorkItemType.task.value,
            'Sub-task': JiraWorkItemType.sub_task.value
        }

    @staticmethod
    def jira_time_to_utc_time_string(jira_time_string):
        try:
            return datetime.strftime(
                datetime.fromtimestamp(JiraProject.parse_jira_time_string(jira_time_string).timestamp()),
                "%Y-%m-%dT%H:%M:%S.%f%z"
            )
        except ValueError as exc:
            logger.warning(f"Jira timestamp {jira_time_string} "
                           f"could not be parsed to UTC returning the original string instead.")
            return jira_time_string

    @staticmethod
    def parse_jira_time_string(jira_time_string):
        return datetime.strptime(jira_time_string, "%Y-%m-%dT%H:%M:%S.%f%z")

    @staticmethod
    def jira_time_string(timestamp):
        return timestamp.strftime("%Y-%m-%d %H:%M")

    def map_issue_to_work_item_data(self, issue, changelog=None):
        fields = issue.get('fields')
        issue_type = fields.get('issuetype').get('name')

        epic_link = find(self.work_items_source.custom_fields, lambda field: field['name'] == 'Epic Link')
        epic_link_custom_field = epic_link.get('key') if epic_link else None
        mapped_data = dict(
                name=fields.get('summary'),
                description=fields.get('description'),
                is_bug=issue_type == 'Bug',
                work_item_type=self.work_item_type_map.get(issue_type, JiraWorkItemType.story.value),
                tags=fields.get('labels', []),
                url=issue.get('self'),
                source_id=str(issue.get('id')),
                source_display_id=issue.get('key'),
                source_last_updated=self.jira_time_to_utc_time_string(fields.get('updated')),
                source_created_at=self.jira_time_to_utc_time_string(fields.get('created')),
                source_state=fields.get('status').get('name'),
                is_epic=issue_type == 'Epic',
                epic_source_display_id=issue.get('fields').get(epic_link_custom_field) if epic_link_custom_field else None
        )

        return mapped_data

    def get_server_timezone_offset(self):
        # This is an awful hack to get around Jira APIs
        # completely boneheaded implementation of time based querying.
        # Since they dont allow specifying timezones in the JQL, we have to
        # guess what timezone they want. /serverinfo is supposed to give us
        # a reference timestamp, but it does not recognize JWT authentication which we
        # use, so what we are doing here is to fetch the issue that was was last updated
        # from our perspective and get the update_at date on that issue to see what the
        # timezone of that date is. It is a truly awful solution, but POS products like Jira force
        # us to do awful things.
        if self.last_updated_issue_source_id is not None:
            response = self.jira_connector.get(
                f'/issue/{self.last_updated_issue_source_id}',
                headers={"Accept": "application/json"}
            )
            if response.ok:
                result = response.json()
                if result is not None:
                    last_updated = JiraProject.parse_jira_time_string(result['fields']['updated'])

                    return last_updated.utcoffset()

    def fetch_work_items_to_sync(self):

        jql_base = f"project = {self.project_id} "

        if self.work_items_source.last_synced is None or self.last_updated is None:
            jql = f'{jql_base} AND created >= "-{self.initial_import_days}d"'
        else:
            server_timezone_offset = self.get_server_timezone_offset() or timedelta(seconds=0)
            # We need this rigmarole because expects dates in the servers timezone. We add 1 minute because the moronic
            # JIRA api does not allow seconds precision in specifying dates so we have to round it up to the next minute
            # so we dont get back the last item that was updated.
            jql = f'{jql_base} AND updated > "{self.jira_time_string(self.last_updated + server_timezone_offset + timedelta(minutes=1))}"'

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

    def fetch_work_items_for_epic(self, epic):
        epic_source_id = epic['source_id']
        jql_base = f"project = {self.project_id} "
        jql = f'{jql_base} AND parent={epic_source_id} OR \"Epic Link\" = {epic_source_id}'

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
