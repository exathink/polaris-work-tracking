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
from polaris.common.enums import PivotalTrackerWorkItemType, WorkTrackingIntegrationType
from polaris.work_tracking import connector_factory

logger = logging.getLogger('polaris.work_tracking.pivotal_tracker')


class PivotalWorkItemSourceType(Enum):
    project = 'project'


class PivotalApiClientMixin:
    def __init__(self, connector):
        self.connector = connector
        self.access_token = connector.api_key
        self.base_url = f'{connector.base_url}/services/v5'


class PivotalTrackerConnector(PivotalApiClientMixin):
    def __init__(self, connector):
        super().__init__(connector)
        self.key = connector.key
        self.name = connector.name
        self.account_key = connector.account_key

    def fetch_projects(self):
        response = requests.get(
            f'{self.base_url}/projects',
            headers={"X-TrackerToken": self.access_token},
        )
        if response.ok:
            return response.json()

        else:
            raise ProcessingException(f'Error fetching projects from connector:'
                                      f' {self.connector.name} : '
                                      f'{response.status_code}: '
                                      f'{response.text}')




    @staticmethod
    def map_project_to_work_items_sources_data(project):
        return dict(
            integration_type=WorkTrackingIntegrationType.pivotal.value,
            work_items_source_type=PivotalWorkItemSourceType.project.value,
            commit_mapping_scope='organization',
            source_id=project['id'],
            name=project['name'],
            url=project.get('url'),
            description=project.get('description')

        )

    def fetch_work_items_sources_to_sync(self, batch_size=100):
        yield [
            self.map_project_to_work_items_sources_data(project)
            for project in self.fetch_projects()
        ]



class PivotalTrackerWorkItemsSource:

    @staticmethod
    def create(token_provider, work_items_source):
        if work_items_source.work_items_source_type == PivotalWorkItemSourceType.project.value:
            return PivotalTrackerProject(token_provider, work_items_source)
        else:
            raise ProcessingException(f"Unknown work items source type {work_items_source.work_items_source_type}")


class PivotalTrackerProject(PivotalTrackerWorkItemsSource):

    def __init__(self, token_provider, work_items_source):

        self.work_items_source = work_items_source
        self.pivotal_connector = connector_factory.get_connector(
            connector_key=self.work_items_source.connector_key
        )
        self.access_token = self.pivotal_connector.api_key
        self.project_id = work_items_source.source_id
        self.base_url = f'${self.pivotal_connector.base_url}/services/v5'
        self.last_updated = work_items_source.latest_work_item_update_timestamp


    def fetch_work_items_to_sync(self):
        query_params = dict(limit=100)
        if self.last_updated:
            query_params['updated_after'] = self.last_updated.isoformat()

        response = requests.get(
            f'{self.base_url}/projects/{self.project_id}/stories',
            headers={"X-TrackerToken": self.access_token},
            params=query_params
        )
        if response.ok:
            offset = 0
            total = int(response.headers.get('X-Tracker-Pagination-Total'))
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


