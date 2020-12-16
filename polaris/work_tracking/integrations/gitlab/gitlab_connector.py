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

    def map_repository_to_work_items_sources_data(self, repository):
        return dict(
            integration_type=WorkTrackingIntegrationType.gitlab.value,
            work_items_source_type=GitlabWorkItemSourceType.repository_issues.value,
            parameters=dict(
                repository=repository['name']
            ),
            commit_mapping_scope='repository',
            source_id=repository['id'],
            name=repository['name'],
            url=repository["_links"]['issues'],
            description=repository['description'],
            custom_fields=[]
        )

    def fetch_repositories(self):
        fetch_repos_url = f'{self.base_url}/projects'
        while fetch_repos_url is not None:
            response = requests.get(
                fetch_repos_url,
                params=dict(membership=True),
                headers={"Authorization": f"Bearer {self.personal_access_token}"},
            )
            if response.ok:
                yield response.json()
                if 'next' in response.links:
                    fetch_repos_url = response.links['next']['url']
                else:
                    fetch_repos_url = None
            else:
                raise ProcessingException(
                    f"Server test failed {response.text} status: {response.status_code}\n"
                )

    def fetch_work_items_sources_to_sync(self):
        for repositories in self.fetch_repositories():
            yield [
                self.map_repository_to_work_items_sources_data(repo)
                for repo in repositories
                if repo['issues_enabled']
            ]


class GitlabWorkItemSourceType(Enum):
    repository_issues = 'repository_issues'


class GitlabIssuesWorkItemsSource:

    @staticmethod
    def create(token_provider, work_items_source):
        if work_items_source.work_items_source_type == GitlabWorkItemSourceType.repository_issues.value:
            return GitlabRepositoryIssues(token_provider, work_items_source)

        else:
            raise ProcessingException(f"Unknown work items source type {work_items_source.work_items_source_type}")


class GitlabRepositoryIssues(GitlabIssuesWorkItemsSource):

    def __init__(self, token_provider, work_items_source):
        self.work_items_source = work_items_source
        self.last_updated = work_items_source.latest_work_item_update_timestamp

        self.gitlab_connector = connector_factory.get_connector(
            connector_key=self.work_items_source.connector_key
        )
