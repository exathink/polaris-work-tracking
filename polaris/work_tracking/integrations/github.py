# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging
from datetime import datetime, timedelta
from enum import Enum

from polaris.common.enums import GithubWorkItemType, WorkTrackingIntegrationType
from polaris.utils.collections import find
from polaris.utils.exceptions import ProcessingException
from polaris.work_tracking import connector_factory

from polaris.integrations.github import GithubConnector


logger = logging.getLogger('polaris.work_tracking.github')


class GithubWorkTrackingConnector(GithubConnector):

    def map_repository_to_work_items_sources_data(self, repository):
        return dict(
            integration_type=WorkTrackingIntegrationType.github.value,
            work_items_source_type=GithubWorkItemSourceType.repository_issues.value,
            parameters=dict(
                github_organization=self.github_organization,
                repository=repository.name
            ),
            commit_mapping_scope='organization',
            source_id=repository.id,
            name=repository.name,
            url=f'{repository.html_url}/issues',
            description=repository.description,

        )

    def fetch_work_items_sources_to_sync(self, batch_size=100):
        repos_paginator = self.fetch_repositories()
        while repos_paginator._couldGrow():
            yield [
                self.map_repository_to_work_items_sources_data(repo)
                for repo in repos_paginator._fetchNextPage()
                if repo.has_issues
            ]

class GithubWorkItemSourceType(Enum):
    repository_issues = 'repository_issues'



class GithubIssuesWorkItemsSource:

    @staticmethod
    def create(token_provider, work_items_source):
        if work_items_source.work_items_source_type == GithubWorkItemSourceType.repository_issues.value:
            return GithubRepositoryIssues(token_provider, work_items_source)

        else:
            raise ProcessingException(f"Unknown work items source type {work_items_source.work_items_source_type}")


class GithubRepositoryIssues(GithubIssuesWorkItemsSource):

    def __init__(self, token_provider, work_items_source):
        self.work_items_source = work_items_source
        self.last_updated = work_items_source.latest_work_item_update_timestamp

        self.github_connector = connector_factory.get_connector(
            connector_key=self.work_items_source.connector_key
        )
        self.github = self.github_connector.get_github_client()

    def map_issue_to_work_item(self, issue):
        bug_tags = ['bug', *self.work_items_source.parameters.get('bug_tags', [])]

        # map common fields first
        work_item = dict(
            name=issue.title[:255],
            description=issue.body,
            is_bug=find(issue.labels, lambda label: label.name in bug_tags) is not None,
            tags=[label.name for label in issue.labels],
            source_id=str(issue.id),
            source_last_updated=issue.updated_at,
            source_created_at=issue.created_at,
            source_display_id=issue.number,
            source_state=issue.state
        )
        if issue.pull_request is not None:
            return dict(
                work_item_type=GithubWorkItemType.pull_request.value,
                url=issue.pull_request.html_url,
                **work_item
            )
        else:
            return dict(
                work_item_type=GithubWorkItemType.issue.value,
                url=issue.url,
                **work_item
            )

    def fetch_work_items_to_sync(self):
        organization = self.work_items_source.parameters.get('github_organization')
        repository = self.work_items_source.parameters.get('repository')
        repo = self.github.get_repo(f"{organization}/{repository}")

        if self.work_items_source.last_synced is None or self.last_updated is None:
            issues_iterator = repo.get_issues(
                state='all',
                sort='created',
                direction='desc',
                since=(
                    datetime.utcnow() -
                    timedelta(days=int(self.work_items_source.parameters.get('initial_import_days', 90)))
                )
            )
        else:
            issues_iterator = repo.get_issues(
                state='all',
                since=self.last_updated
            )

        fetched = 0
        while issues_iterator._couldGrow():
            work_items = [
                self.map_issue_to_work_item(issue)
                for issue in issues_iterator._fetchNextPage()
            ]
            if len(work_items) == 0:
                logger.info('There are no work items to import')

            fetched = fetched + len(work_items)
            yield work_items
