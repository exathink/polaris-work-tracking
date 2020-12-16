# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal

import logging
import requests
from enum import Enum
from datetime import datetime, timedelta
from polaris.utils.collections import find

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
                # TODO: Check if we need to add bug tags like github
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
    def create(work_items_source):
        if work_items_source.work_items_source_type == GitlabWorkItemSourceType.repository_issues.value:
            return GitlabRepositoryIssues(work_items_source)

        else:
            raise ProcessingException(f"Unknown work items source type {work_items_source.work_items_source_type}")


class GitlabRepositoryIssues(GitlabIssuesWorkItemsSource):

    def __init__(self, work_items_source):
        self.work_items_source = work_items_source
        self.gitlab_connector = connector_factory.get_connector(
            connector_key=self.work_items_source.connector_key
        )
        self.source_project_id = work_items_source.source_id
        self.last_updated = work_items_source.latest_work_item_update_timestamp
        self.personal_access_token = self.gitlab_connector.personal_access_token

    def map_issue_to_work_item(self, issue):
        bug_tags = ['bug', *self.work_items_source.parameters.get('bug_tags', [])]
        work_item = dict(
            name=issue.title[:255],
            description=issue.description,
            is_bug=find(issue.labels, lambda label: label.name in bug_tags) is not None,
            tags=[label for label in issue.labels],
            source_id=str(issue.id),
            source_last_updated=issue.updated_at,
            source_created_at=issue.created_at,
            source_display_id=issue.iid,
            source_state=issue.state,
            is_epic=False,
            url=issue.web_url,
            api_payload=issue.raw_data
        )

    def fetch_work_items(self):
        query_params = dict(limit=100)
        if self.work_items_source.last_synced is None or self.last_updated is None:
            query_params['updated_after'] = (datetime.utcnow() - timedelta(
                days=int(self.work_items_source.parameters.get('initial_import_days', 90))))
        else:
            query_params['updated_after'] = self.last_updated.isoformat()
        fetch_issues_url = f'{self.base_url}/projects/{self.source_project_id}/issues'
        while fetch_issues_url is not None:
            response = requests.get(
                fetch_issues_url,
                params=query_params,
                headers={"Authorization": f"Bearer {self.personal_access_token}"},
            )
            if response.ok:
                yield response.json()
                if 'next' in response.links:
                    fetch_issues_url = response.links['next']['url']
                else:
                    fetch_issues_url = None
            else:
                raise ProcessingException(
                    f"Fetch from server failed {response.text} status: {response.status_code}\n"
                )

    def fetch_work_items_to_sync(self):
        for issues in self.fetch_work_items():
            yield [
                self.map_issue_to_work_item(issue)
                for issue in issues
            ]
