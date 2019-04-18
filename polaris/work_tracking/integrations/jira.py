# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from enum import Enum
import requests
import logging
from polaris.utils.exceptions import ProcessingException
from polaris.common.enums import PivotalTrackerWorkItemType
logger = logging.getLogger('polaris.work_tracking.jira')


class JiraWorkItemSourceType(Enum):
    project = 'project'


class JiraWorkItemsSource:

    @staticmethod
    def create(token_provider, work_items_source):
        if work_items_source.work_items_source_type == JiraWorkItemSourceType.project.value:
            return JiraProject(token_provider, work_items_source)
        else:
            raise ProcessingException(f"Unknown work items source type {work_items_source.work_items_source_type}")

class JiraProject(JiraWorkItemsSource):

    def __init__(self, token_provider, work_items_source):
        self.access_token = token_provider.get_token(work_items_source.account_key, work_items_source.organization_key,
                                                     'jira_api_key')
        self.work_items_source = work_items_source
        self.server_url = work_items_source.parameters.get('server_url')
        self.base_url = f'{self.base_url}/rest/api/2'
        self.project_key = work_items_source.parameters.get('project_key')
        self.initial_import_days = work_items_source.parameters.get('initial_import_days')
        self.last_updated = work_items_source.latest_work_item_update_timestamp

    def fetch_work_items_to_sync(self):

        jql_base = f"project={self.project_key} "

        if self.work_items_source.last_synced is None or self.last_updated is None:
            jql=f'{jql_base} AND created >= "-{self.initial_import_days}d"'
        else:
            jql = f'{jql_base} AND updated > "{self.last_updated.isoformat()}"'

        response = requests.get(
            f'{self.base_url}/search',
            headers={"Accept": "application/json", "Bearer": self.access_token},
            params= dict(
                fields="summary,created,updated, description,labels,issuetype,status",
                jql=jql,
                maxResults=100
            )
        )
        if response.ok:
            offset = 0
            total = int(response.get('total') or 0)
            while offset < total and response.ok:
                stories = response.json()
                if len(stories) == 0:
                    break

                work_items = [
                    dict(
                        name=story.get('name'),
                        description=story.get('description'),
                   is_bug=story.get('story_type') == 'bug',
                        work_item_type=PivotalTrackerWorkItemType.story.value,
                        tags=[story.get('story_type')] + [label.get('name') for label in story.get('labels')],
                        url=story.get('url'),
                        source_id=str(story.get('id')),
                        source_last_updated=story.get('updated_at'),
                        source_created_at=story.get('created_at'),
                        source_display_id=story.get('id'),
                        source_state=story.get('current_state')

                    )
                    for story in stories
                ]
                yield work_items

                offset = offset + len(work_items)
                query_params['offset'] = offset
                response = requests.get(
                    f'{self.base_url}/projects/{self.project_id}/stories',
                    headers={"X-TrackerToken": self.access_token},
                    params=query_params
                )
                total = int(response.headers.get('X-Tracker-Pagination-Total'))


