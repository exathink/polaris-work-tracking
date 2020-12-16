# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal

import logging
import requests
from enum import Enum
from polaris.common.enums import WorkTrackingIntegrationType
from polaris.integrations.gitlab import GitlabConnector
from polaris.utils.exceptions import ProcessingException
from polaris.work_tracking import connector_factory

logger = logging.getLogger('polaris.work_tracking.gitlab')


class GitlabWorkTrackingConnector(GitlabConnector):

    def __init__(self, connector):
        super().__init__(connector)

    def map_project_to_work_items_sources_data(self, project):
        return dict(
            integration_type=WorkTrackingIntegrationType.gitlab.value,
            work_items_source_type=GitlabWorkItemSourceType.projects.value,
            parameters=dict(
                repository=project['name']
            ),
            commit_mapping_scope='repository',
            source_id=project['id'],
            name=project['name'],
            url=project["_links"]['issues'],
            description=project['description'],
            custom_fields=[]
        )

    def fetch_gitlab_projects(self):
        fetch_projects_url = f'{self.base_url}/projects'
        while fetch_projects_url is not None:
            response = requests.get(
                fetch_projects_url,
                params=dict(membership=True, with_issues_enabled=True),
                headers={"Authorization": f"Bearer {self.personal_access_token}"},
            )
            if response.ok:
                yield response.json()
                if 'next' in response.links:
                    fetch_projects_url = response.links['next']['url']
                else:
                    fetch_projects_url = None
            else:
                raise ProcessingException(
                    f"Server test failed {response.text} status: {response.status_code}\n"
                )

    def fetch_work_items_sources_to_sync(self):
        for projects in self.fetch_gitlab_projects():
            yield [
                self.map_project_to_work_items_sources_data(project)
                for project in projects
            ]


class GitlabWorkItemSourceType(Enum):
    projects = 'projects'


class GitlabIssuesWorkItemsSource:

    @staticmethod
    def create(token_provider, work_items_source):
        if work_items_source.work_items_source_type == GitlabWorkItemSourceType.projects.value:
            return GitlabProject(token_provider, work_items_source)

        else:
            raise ProcessingException(f"Unknown work items source type {work_items_source.work_items_source_type}")


class GitlabProject(GitlabIssuesWorkItemsSource):

    def __init__(self, token_provider, work_items_source):
        self.work_items_source = work_items_source
        self.last_updated = work_items_source.latest_work_item_update_timestamp

        self.gitlab_connector = connector_factory.get_connector(
            connector_key=self.work_items_source.connector_key
        )
