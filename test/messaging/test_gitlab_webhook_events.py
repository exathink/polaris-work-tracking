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


@pytest.yield_fixture
def setup_project_and_work_items_sources(setup_connectors):
    connector_keys = setup_connectors
    work_items_sources_keys = dict(
        gitlab=uuid.uuid4(),
        github=uuid.uuid4(),
        pivotal_tracker=uuid.uuid4()
    )
    with db.orm_session() as session:
        project = model.Project(
            name='TestProject',
            key=uuid.uuid4(),
            organization_key=polaris_organization_key,
            account_key=exathink_account_key
        )

        project.work_items_sources.append(
            model.WorkItemsSource(
                key=work_items_sources_keys['gitlab'],
                connector_key=connector_keys['gitlab'],
                integration_type='gitlab',
                work_items_source_type='project',
                parameters=dict(id="1934657", name="polaris-web"),
                name='polaris-web',
                account_key=exathink_account_key,
                organization_key=polaris_organization_key,
                commit_mapping_scope='organization',
                commit_mapping_scope_key=polaris_organization_key,
                import_state=WorkItemsSourceImportState.ready.value
            )
        )

        session.add(project)

        session.flush()
        yield project, work_items_sources_keys, connector_keys


class TestGitlabWebhookEvents:
    class TestGitlabIssueEvents:

        @pytest.yield_fixture()
        def setup(self, setup_project_and_work_items_sources):
            project, work_items_sources_key, connector_keys = setup_project_and_work_items_sources
            connector_key = connector_keys['gitlab']
            event_type = 'issue'
            yield Fixture(
                organization_key=polaris_organization_key,
                connector_key=connector_key,
                event_type=event_type
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
                        "id": 9576833,
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
                        "project_id": 9576833,
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
                        "labels": [],
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
                            "current": 9576833
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

            def it_creates_new_issue(self, setup):
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
                    subscriber = WorkItemsTopicSubscriber(channel, publisher=publisher)
                    subscriber.consumer_context = mock_consumer
                    message = subscriber.dispatch(channel, gitlab_new_issue_event)
                    #assert message
                    source_issue_id = str(fixture.new_payload['object_attributes']['id'])
                    url = str(fixture.new_payload['object_attributes']['url'])
                    assert db.connection().execute(
                        f"select count(id) from work_tracking.work_items \
                        where source_id='{source_issue_id}' and url='{url}'"
                    ).scalar() == 1
                    assert_topic_and_message(publish, WorkItemsTopic, WorkItemsCreated)
