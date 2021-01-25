# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal

import uuid
import json
import pytest

from unittest.mock import MagicMock, patch
from polaris.common import db
from test.constants import *
from polaris.utils.collections import Fixture
from polaris.work_tracking.db import model
from polaris.messaging.message_consumer import MessageConsumer
from polaris.utils.token_provider import get_token_provider
from polaris.common.enums import WorkItemsSourceImportState

from polaris.messaging.test_utils import fake_send, mock_publisher, mock_channel, assert_topic_and_message

from polaris.messaging.topics import WorkItemsTopic
from polaris.messaging.messages import WorkItemsCreated, WorkItemsUpdated
from polaris.work_tracking.messages import GitlabProjectEvent
from polaris.work_tracking.message_listener import WorkItemsTopicSubscriber

mock_consumer = MagicMock(MessageConsumer)
mock_consumer.token_provider = get_token_provider()


# Publish both types of events and validate the changes


class TestGitlabWebhookEvents:
    class TestGitlabIssueEvents:

        @pytest.yield_fixture()
        def setup(self, setup_work_item_sources, cleanup):
            session, work_items_sources = setup_work_item_sources
            session.commit()
            connector_key = work_items_sources['gitlab'].connector_key
            event_type = 'issue'
            yield Fixture(
                organization_key=polaris_organization_key,
                connector_key=connector_key,
                event_type=event_type,
                work_items_source=work_items_sources['gitlab']
            )

        class TestNewIssueEvent:

            @pytest.yield_fixture()
            def setup(self, setup):
                fixture = setup

                payload = {
                    "object_kind": "issue",
                    "event_type": "issue",
                    "user": {
                        "id": 5257663,
                        "name": "Pragya Goyal",
                        "username": "pragya3",
                        "avatar_url": "https://secure.gravatar.com/avatar/f4e5904c494e37510101ac9ce50e7ddf?s=80&d=identicon",
                        "email": "pragya@64sqs.com"
                    },
                    "project": {
                        "id": gitlab_work_items_source_id,
                        "name": "test-repo",
                        "description": "",
                        "web_url": "https://gitlab.com/polaris-test/test-repo",
                        "avatar_url": None,
                        "git_ssh_url": "git@gitlab.com:polaris-test/test-repo.git",
                        "git_http_url": "https://gitlab.com/polaris-test/test-repo.git",
                        "namespace": "polaris-test",
                        "visibility_level": 0,
                        "path_with_namespace": "polaris-test/test-repo",
                        "default_branch": "master",
                        "ci_config_path": None,
                        "homepage": "https://gitlab.com/polaris-test/test-repo",
                        "url": "git@gitlab.com:polaris-test/test-repo.git",
                        "ssh_url": "git@gitlab.com:polaris-test/test-repo.git",
                        "http_url": "https://gitlab.com/polaris-test/test-repo.git"
                    },
                    "object_attributes": {
                        "author_id": 5257663,
                        "closed_at": None,
                        "confidential": False,
                        "created_at": "2021-01-14 10:24:20 UTC",
                        "description": "",
                        "discussion_locked": None,
                        "due_date": None,
                        "id": 77215100,
                        "iid": 9,
                        "last_edited_at": None,
                        "last_edited_by_id": None,
                        "milestone_id": None,
                        "moved_to_id": None,
                        "duplicated_to_id": None,
                        "project_id": gitlab_work_items_source_id,
                        "relative_position": None,
                        "state_id": 1,
                        "time_estimate": 0,
                        "title": "New issue for unit tests",
                        "updated_at": "2021-01-14 10:24:20 UTC",
                        "updated_by_id": None,
                        "weight": None,
                        "url": "https://gitlab.com/polaris-test/test-repo/-/issues/9",
                        "total_time_spent": 0,
                        "human_total_time_spent": None,
                        "human_time_estimate": None,
                        "assignee_ids": [],
                        "assignee_id": None,
                        "labels": ["IN-PROGRESS"],
                        "state": "opened",
                        "action": "open"
                    },
                    "labels": [],
                    "changes": {
                        "author_id": {
                            "previous": None,
                            "current": 5257663
                        },
                        "created_at": {
                            "previous": None,
                            "current": "2021-01-14 10:24:20 UTC"
                        },
                        "description": {
                            "previous": None,
                            "current": ""
                        },
                        "id": {
                            "previous": None,
                            "current": 77215100
                        },
                        "iid": {
                            "previous": None,
                            "current": 9
                        },
                        "project_id": {
                            "previous": None,
                            "current": gitlab_work_items_source_id
                        },
                        "title": {
                            "previous": None,
                            "current": "New issue for unit tests"
                        },
                        "updated_at": {
                            "previous": None,
                            "current": "2021-01-14 10:24:20 UTC"
                        }
                    },
                    "repository": {
                        "name": "test-repo",
                        "url": "git@gitlab.com:polaris-test/test-repo.git",
                        "description": "",
                        "homepage": "https://gitlab.com/polaris-test/test-repo"
                    }
                }
                yield Fixture(
                    parent=fixture,
                    new_payload=payload
                )

            def it_creates_new_work_item(self, setup):
                fixture = setup
                gitlab_new_issue_event = fake_send(
                    GitlabProjectEvent(
                        send=dict(
                            event_type=fixture.event_type,
                            connector_key=fixture.connector_key,
                            payload=json.dumps(fixture.new_payload)
                        )
                    )
                )
                publisher = mock_publisher()
                channel = mock_channel()
                with patch('polaris.work_tracking.publish.publish') as publish:
                    with patch(
                            'polaris.work_tracking.integrations.gitlab.GitlabProject.fetch_project_boards') as fetch_project_boards:
                        fetch_project_boards.return_value = [
                            [
                                {
                                    "id": 2245441,
                                    "name": "Development",
                                    "hide_backlog_list": False,
                                    "hide_closed_list": False,
                                    "lists": [
                                        {
                                            "id": 6786201,
                                            "label": {
                                                "id": 17640856,
                                                "name": "IN-PROGRESS",
                                                "color": "#5CB85C",
                                                "description": "Indicates in progress issues",
                                                "description_html": "Indicates in progress issues",
                                                "text_color": "#FFFFFF"
                                            },
                                            "position": 0
                                        },
                                        {
                                            "id": 6786202,
                                            "label": {
                                                "id": 17640857,
                                                "name": "DEV-DONE",
                                                "color": "#A295D6",
                                                "description": None,
                                                "description_html": "",
                                                "text_color": "#333333"
                                            },
                                            "position": 1
                                        }
                                    ]
                                },
                                {
                                    "id": 2282923,
                                    "name": "Product",
                                    "hide_backlog_list": False,
                                    "hide_closed_list": False,
                                    "lists": [
                                        {
                                            "id": 6786204,
                                            "label": {
                                                "id": 17640863,
                                                "name": "DEPLOYED",
                                                "color": "#428BCA",
                                                "description": "Story has been deployed",
                                                "description_html": "Story has been deployed",
                                                "text_color": "#FFFFFF"
                                            },
                                            "position": 0
                                        }
                                    ],
                                }
                            ]
                        ]
                        subscriber = WorkItemsTopicSubscriber(channel, publisher=publisher)
                        subscriber.consumer_context = mock_consumer
                        message = subscriber.dispatch(channel, gitlab_new_issue_event)
                        assert message
                        source_issue_id = str(fixture.new_payload['object_attributes']['id'])
                        url = str(fixture.new_payload['object_attributes']['url'])
                        assert db.connection().execute(
                            f"select count(id) from work_tracking.work_items \
                            where source_id='{source_issue_id}' and url='{url}' \
                            and source_state='IN-PROGRESS'"
                        ).scalar() == 1
                        # Check if source_data and source_states are updated in work_items_source
                        assert db.connection().execute(
                            f"select count(id) from work_tracking.work_items_sources \
                                                                        where key='{fixture.work_items_source.key}' \
                                                                        and source_data->'boards' is not NULL \
                                                                        and source_states is not NULL"
                        ).scalar() == 1
                        assert_topic_and_message(publish, WorkItemsTopic, WorkItemsCreated)

            class TestUpdateIssueEvent:
                @pytest.yield_fixture()
                def setup(self, setup):
                    fixture = setup

                    payload = {
                        "object_kind": "issue",
                        "event_type": "issue",
                        "user": {
                            "id": 5257663,
                            "name": "Pragya Goyal",
                            "username": "pragya3",
                            "avatar_url": "https://secure.gravatar.com/avatar/f4e5904c494e37510101ac9ce50e7ddf?s=80&d=identicon",
                            "email": "pragya@64sqs.com"
                        },
                        "project": {
                            "id": gitlab_work_items_source_id,
                            "name": "test-repo",
                            "description": "",
                            "web_url": "https://gitlab.com/polaris-test/test-repo",
                            "avatar_url": None,
                            "git_ssh_url": "git@gitlab.com:polaris-test/test-repo.git",
                            "git_http_url": "https://gitlab.com/polaris-test/test-repo.git",
                            "namespace": "polaris-test",
                            "visibility_level": 0,
                            "path_with_namespace": "polaris-test/test-repo",
                            "default_branch": "master",
                            "ci_config_path": None,
                            "homepage": "https://gitlab.com/polaris-test/test-repo",
                            "url": "git@gitlab.com:polaris-test/test-repo.git",
                            "ssh_url": "git@gitlab.com:polaris-test/test-repo.git",
                            "http_url": "https://gitlab.com/polaris-test/test-repo.git"
                        },
                        "object_attributes": {
                            "author_id": 5257663,
                            "closed_at": "2021-01-15 08:28:12 UTC",
                            "confidential": False,
                            "created_at": "2021-01-14 10:24:20 UTC",
                            "description": "Edit 1",
                            "discussion_locked": None,
                            "due_date": None,
                            "id": 77215100,
                            "iid": 9,
                            "last_edited_at": "2021-01-15 08:20:24 UTC",
                            "last_edited_by_id": 5257663,
                            "milestone_id": None,
                            "moved_to_id": None,
                            "duplicated_to_id": None,
                            "project_id": gitlab_work_items_source_id,
                            "relative_position": 4617,
                            "state_id": 2,
                            "time_estimate": 0,
                            "title": "New issue for unit tests",
                            "updated_at": "2021-01-15 08:28:12 UTC",
                            "updated_by_id": 5257663,
                            "weight": None,
                            "url": "https://gitlab.com/polaris-test/test-repo/-/issues/9",
                            "total_time_spent": 0,
                            "human_total_time_spent": None,
                            "human_time_estimate": None,
                            "assignee_ids": [],
                            "assignee_id": None,
                            "labels": [],
                            "state": "closed",
                            "action": "close"
                        },
                        "labels": [],
                        "changes": {
                            "updated_at": {
                                "previous": "2021-01-15 08:28:12 UTC",
                                "current": "2021-01-15 08:28:12 UTC"
                            }
                        },
                        "repository": {
                            "name": "test-repo",
                            "url": "git@gitlab.com:polaris-test/test-repo.git",
                            "description": "",
                            "homepage": "https://gitlab.com/polaris-test/test-repo"
                        }
                    }

                    yield Fixture(
                        parent=fixture,
                        update_payload=payload
                    )

                def it_updates_existing_work_item(self, setup):
                    fixture = setup
                    gitlab_new_issue_event = fake_send(
                        GitlabProjectEvent(
                            send=dict(
                                event_type=fixture.event_type,
                                connector_key=fixture.connector_key,
                                payload=json.dumps(fixture.new_payload)
                            )
                        )
                    )

                    gitlab_update_issue_event = fake_send(
                        GitlabProjectEvent(
                            send=dict(
                                event_type=fixture.event_type,
                                connector_key=fixture.connector_key,
                                payload=json.dumps(fixture.update_payload)
                            )
                        )
                    )
                    publisher = mock_publisher()
                    channel = mock_channel()
                    subscriber = WorkItemsTopicSubscriber(channel, publisher=publisher)
                    subscriber.consumer_context = mock_consumer

                    with patch('polaris.work_tracking.publish.publish') as publish:
                        with patch(
                                'polaris.work_tracking.integrations.gitlab.GitlabProject.fetch_project_boards') as fetch_project_boards:
                            fetch_project_boards.return_value = [
                                [
                                    {
                                        "id": 2245441,
                                        "name": "Development",
                                        "hide_backlog_list": False,
                                        "hide_closed_list": False,
                                        "lists": [
                                            {
                                                "id": 6786201,
                                                "label": {
                                                    "id": 17640856,
                                                    "name": "IN-PROGRESS",
                                                    "color": "#5CB85C",
                                                    "description": "Indicates in progress issues",
                                                    "description_html": "Indicates in progress issues",
                                                    "text_color": "#FFFFFF"
                                                },
                                                "position": 0
                                            },
                                            {
                                                "id": 6786202,
                                                "label": {
                                                    "id": 17640857,
                                                    "name": "DEV-DONE",
                                                    "color": "#A295D6",
                                                    "description": None,
                                                    "description_html": "",
                                                    "text_color": "#333333"
                                                },
                                                "position": 1
                                            }
                                        ]
                                    },
                                    {
                                        "id": 2282923,
                                        "name": "Product",
                                        "hide_backlog_list": False,
                                        "hide_closed_list": False,
                                        "lists": [
                                            {
                                                "id": 6786204,
                                                "label": {
                                                    "id": 17640863,
                                                    "name": "DEPLOYED",
                                                    "color": "#428BCA",
                                                    "description": "Story has been deployed",
                                                    "description_html": "Story has been deployed",
                                                    "text_color": "#FFFFFF"
                                                },
                                                "position": 0
                                            }
                                        ],
                                    }
                                ]
                            ]
                            subscriber.dispatch(channel, gitlab_new_issue_event)
                            assert_topic_and_message(publish, WorkItemsTopic, WorkItemsCreated)

                    with patch('polaris.work_tracking.publish.publish') as publish:
                        with patch(
                                'polaris.work_tracking.integrations.gitlab.GitlabProject.fetch_project_boards') as fetch_project_boards:
                            fetch_project_boards.return_value = [
                                [
                                    {
                                        "id": 2245441,
                                        "name": "Development",
                                        "hide_backlog_list": False,
                                        "hide_closed_list": False,
                                        "lists": [
                                            {
                                                "id": 6786201,
                                                "label": {
                                                    "id": 17640856,
                                                    "name": "IN-PROGRESS",
                                                    "color": "#5CB85C",
                                                    "description": "Indicates in progress issues",
                                                    "description_html": "Indicates in progress issues",
                                                    "text_color": "#FFFFFF"
                                                },
                                                "position": 0
                                            },
                                            {
                                                "id": 6786202,
                                                "label": {
                                                    "id": 17640857,
                                                    "name": "DEV-DONE",
                                                    "color": "#A295D6",
                                                    "description": None,
                                                    "description_html": "",
                                                    "text_color": "#333333"
                                                },
                                                "position": 1
                                            }
                                        ]
                                    },
                                    {
                                        "id": 2282923,
                                        "name": "Product",
                                        "hide_backlog_list": False,
                                        "hide_closed_list": False,
                                        "lists": [
                                            {
                                                "id": 6786204,
                                                "label": {
                                                    "id": 17640863,
                                                    "name": "DEPLOYED",
                                                    "color": "#428BCA",
                                                    "description": "Story has been deployed",
                                                    "description_html": "Story has been deployed",
                                                    "text_color": "#FFFFFF"
                                                },
                                                "position": 0
                                            }
                                        ],
                                    }
                                ]
                            ]
                            message = subscriber.dispatch(channel, gitlab_update_issue_event)
                            assert message
                            source_issue_id = str(fixture.new_payload['object_attributes']['id'])
                            url = str(fixture.new_payload['object_attributes']['url'])
                            assert db.connection().execute(
                                f"select count(id) from work_tracking.work_items \
                                                where source_id='{source_issue_id}' \
                                                and url='{url}' \
                                                and source_state='closed'").scalar() == 1
                            assert_topic_and_message(publish, WorkItemsTopic, WorkItemsUpdated)
