# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from polaris.common.enums import WorkTrackingIntegrationType, JiraWorkItemSourceType
from polaris.integrations.atlassian_connect import PolarisAtlassianConnector
from polaris.utils.exceptions import ProcessingException


class JiraConnector(PolarisAtlassianConnector):

    def __init__(self, connector):
        super().__init__(connector)

    def test(self):
        fetch_projects_url = '/project/search'
        query_params = dict(
            maxResults=1
        )
        response = self.get(
            fetch_projects_url,
            params=query_params,
            headers={"Accept": "application/json"},
        )

        if response.ok:
            return True
        else:
            raise ProcessingException(f'Jira Connector Test Failed: {response.text} ({response.status_code})')

    def fetch_project(self, project_id):
        fetch_project_url = f'/project/{project_id}'
        query_params = dict(
            expand='description, url'
        )
        response = self.get(
            fetch_project_url,
            params=query_params,
            headers={"Accept": "application/json"},
        )

        if response.ok:
            return response.json()
        else:
            raise ProcessingException(f'Failed to fetch projects from connnect {self.key} at offset {offset}: {response.text}')

    def fetch_projects(self, maxResults, offset):
        fetch_projects_url = '/project/search'
        query_params = dict(
            startAt=offset,
            maxResults=maxResults,
            expand='description,url'
        )
        response = self.get(
            fetch_projects_url,
            params=query_params,
            headers={"Accept": "application/json"},
        )

        if response.ok:
            body = response.json()
            return body.get('values'), body.get('total')
        else:
            raise ProcessingException(f'Failed to fetch projects from connnect {self.key} at offset {offset}: {response.text}')

    @staticmethod
    def map_project_to_work_items_sources_data(project):
        return dict(
            integration_type=WorkTrackingIntegrationType.jira.value,
            work_items_source_type=JiraWorkItemSourceType.project.value,
            commit_mapping_scope='organization',
            source_id=project['id'],
            name=project['name'],
            url=project.get('url'),
            description=project.get('description')

        )

    def fetch_work_items_sources_to_sync(self, batch_size=100):
        offset = 0
        projects, total = self.fetch_projects(maxResults=batch_size, offset=offset)
        while projects is not None and offset < total:
            if len(projects) == 0:
                break

            work_items_sources = []
            for project in projects:
                work_items_sources_data = self.map_project_to_work_items_sources_data(project)
                if work_items_sources_data:
                    work_items_sources.append(work_items_sources_data)

            yield work_items_sources

            offset = offset + len(projects)
            projects, total = self.fetch_projects(maxResults=batch_size, offset=offset)

    def fetch_work_items_source_data_for_project(self, project_id):
        return self.map_project_to_work_items_sources_data(self.fetch_project(project_id))





