# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal

import copy
import logging
import requests
from enum import Enum
from datetime import datetime, timedelta
from polaris.utils.collections import find

from polaris.common.enums import WorkTrackingIntegrationType, GitlabWorkItemType
from polaris.integrations.gitlab import GitlabConnector
from polaris.utils.exceptions import ProcessingException
from polaris.work_tracking import connector_factory
from polaris.utils.config import get_config_provider

config_provider = get_config_provider()

logger = logging.getLogger('polaris.work_tracking.gitlab')


class GitlabWorkTrackingConnector(GitlabConnector):

    def __init__(self, connector):
        super().__init__(connector)
        self.webhook_secret = connector.webhook_secret
        self.webhook_events = ['issue_events']

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
            custom_fields=[],
            source_data={}
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

    def register_project_webhooks(self, project_source_id, registered_webhooks):
        deleted_hook_ids = []
        for inactive_hook_id in registered_webhooks:
            if self.delete_project_webhook(project_source_id, inactive_hook_id):
                logger.info(f"Deleted webhook with id {inactive_hook_id} for repo {project_source_id}")
                deleted_hook_ids.append(inactive_hook_id)
            else:
                logger.info(f"Webhook with id {inactive_hook_id} for project {project_source_id} could not be deleted")

        # Register new webhook now
        project_webhooks_callback_url = f"{config_provider.get('GITLAB_WEBHOOKS_BASE_URL')}" \
                                        f"/project/webhooks/{self.key}/"

        add_hook_url = f"{self.base_url}/projects/{project_source_id}/hooks"

        post_data = dict(
            id=project_source_id,
            url=project_webhooks_callback_url,
            push_events=False,
            issues_events=True,
            enable_ssl_verification=True,
            token=self.webhook_secret
        )
        for event in self.webhook_events:
            post_data[f'{event}'] = True

        response = requests.post(
            add_hook_url,
            headers={"Authorization": f"Bearer {self.personal_access_token}"},
            data=post_data
        )
        if response.ok:
            result = response.json()
            active_hook_id = result['id']
        else:
            raise ProcessingException(
                f"Webhook registration failed due to status:{response.status_code} message:{response.text}")
        return dict(
            success=True,
            active_webhook=active_hook_id,
            deleted_webhooks=deleted_hook_ids,
            registered_events=self.webhook_events,
        )

    def delete_project_webhook(self, project_source_id, inactive_hook_id):
        delete_hook_url = f"{self.base_url}/projects/{project_source_id}/hooks/{inactive_hook_id}"
        response = requests.delete(
            delete_hook_url,
            headers={"Authorization": f"Bearer {self.personal_access_token}"}
        )
        if response.ok or response.status_code == 404:
            # Case when hook was already non-existent or deleted successfully
            return True
        else:
            logger.info(
                f"Failed to delete webhooks for project with source id: ({project_source_id})"
                f'{response.status_code} {response.text}'
            )


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

    def __init__(self, token_provider, work_items_source, connector=None):
        self.work_items_source = work_items_source
        self.last_updated = work_items_source.latest_work_item_update_timestamp
        self.source_states = work_items_source.source_states
        self.basic_source_states = ['opened', 'closed']
        self.gitlab_connector = connector if connector else connector_factory.get_connector(
            connector_key=self.work_items_source.connector_key
        )
        self.source_project_id = work_items_source.source_id
        self.personal_access_token = self.gitlab_connector.personal_access_token

    def resolve_work_item_type_for_issue(self, labels):
        lower_case_labels = [label.lower() for label in labels]
        for label in lower_case_labels:
            if label == 'story':
                return GitlabWorkItemType.story.value
            if label == 'enhancement':
                return GitlabWorkItemType.enhancement.value
            if label == 'incident' or label == 'bug' or label == 'defect':
                return GitlabWorkItemType.bug.value
            if label == 'task':
                return GitlabWorkItemType.task.value
        return GitlabWorkItemType.issue.value

    def map_issue_to_work_item(self, issue):
        labels = issue['labels']
        derived_labels = []

        for label in labels:
            if type(label) == str:
                derived_labels.append(label)
            if type(label) == dict:
                new_label = label.get('title')
                if new_label:
                    derived_labels.append(new_label)

        # Resolve source state from labels / state value
        source_state = issue['state']
        if source_state != 'closed':
            for label in derived_labels:
                if label in self.source_states:
                    source_state = label

        work_item_type = self.resolve_work_item_type_for_issue(derived_labels)

        work_item = dict(
            name=issue['title'][:255],
            description=issue['description'],
            is_bug=(work_item_type==GitlabWorkItemType.bug.value),
            tags=derived_labels,
            source_id=str(issue['id']),
            source_last_updated=issue['updated_at'],
            source_created_at=issue['created_at'],
            source_display_id=issue['iid'],
            source_state=source_state,
            is_epic=False,
            url=issue.get('web_url') if issue.get('web_url') else issue.get('url'),
            work_item_type=work_item_type,
            api_payload=issue
        )
        return work_item

    def fetch_work_items(self):
        query_params = dict(limit=100)
        if self.work_items_source.last_synced is None or self.last_updated is None:
            query_params['updated_after'] = (datetime.utcnow() - timedelta(
                days=int(self.work_items_source.parameters.get('initial_import_days', 90))))
        else:
            query_params['updated_after'] = self.last_updated.isoformat()
        fetch_issues_url = f'{self.gitlab_connector.base_url}/projects/{self.source_project_id}/issues'
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

    def fetch_project_boards(self):
        query_params = dict(limit=100)
        fetch_boards_url = f'{self.gitlab_connector.base_url}/projects/{self.source_project_id}/boards'
        while fetch_boards_url is not None:
            response = requests.get(
                fetch_boards_url,
                params=query_params,
                headers={"Authorization": f"Bearer {self.personal_access_token}"},
            )
            if response.ok:
                yield response.json()
                if 'next' in response.links:
                    fetch_boards_url = response.links['next']['url']
                else:
                    fetch_boards_url = None
            else:
                raise ProcessingException(
                    f"Fetch project boards from server failed {response.text} status: {response.status_code}\n"
                )

    def before_work_item_sync(self):
        project_boards = [data for data in self.fetch_project_boards()][0]
        source_data = dict(boards=project_boards)

        intermediate_source_states = []
        for board in project_boards:
            for board_list in board['lists']:
                intermediate_source_states.append(board_list['label']['name'])
        # Update class variable for source_states to latest
        self.source_states = list(set(self.basic_source_states).union(set(intermediate_source_states)))
        return dict(
            source_data=source_data,
            source_states=self.source_states
        )
