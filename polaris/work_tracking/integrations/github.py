# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging

from github import Github
from polaris.work_tracking.db.api import import_work_items
from polaris.utils.collections import find

def github_client(token_provider, work_items_source):
    return Github(per_page=100, login_or_token=token_provider.get_token(work_items_source.account_key, work_items_source.organization_key, 'github_access_token'))

logger = logging.getLogger('polaris.work_tracking.github')

class GithubIssuesWorkItemsSource:

    @staticmethod
    def create(token_provider, work_items_source):
        assert work_items_source.integration_type in ['github', 'github_enterprise']

        if work_items_source.work_items_source_type == 'repository_issues':
            return GithubRepositoryIssues(token_provider, work_items_source)

        

class GithubRepositoryIssues(GithubIssuesWorkItemsSource):

    def __init__(self, token_provider, work_items_source):
        self.github = github_client(token_provider, work_items_source)
        self.work_items_source = work_items_source


    def fetch_new_work_items(self, created_since=None):
        organization = self.work_items_source.parameters.get('organization')
        repository = self.work_items_source.parameters.get('repository')
        bug_tags =  ['bug', *self.work_items_source.parameters.get('bug_tags', [])]

        #query terms
        repository_query_term = f'repo:{organization}/{repository}'
        created_since_query_term = f'created:>{created_since.isoformat()}' if created_since else ''
        query=f'type:issue state:open {repository_query_term} {created_since_query_term}'

        logger.info(f"Importing issues for {repository_query_term}: query={query}")
        issues_iterator = self.github.search_issues(query=query)

        fetched = 0
        while issues_iterator._couldGrow():
            issues = [
                dict(
                    name=issue.title,
                    description=issue.body,
                    is_bug=find(issue.labels, lambda label: label.name in bug_tags) is not None,
                    tags=[label.name for label in issue.labels],
                    url=issue.url,
                    source_id=issue.id,
                    source_last_updated=issue.updated_at,
                    source_created_at=issue.created_at,
                    source_display_id=issue.number,
                    source_state=issue.state

                )
                for issue in issues_iterator._fetchNextPage()
            ]
            if len(issues) == 0:
                logger.info('There are no issues to import')

            fetched = fetched + len(issues)
            yield issues








