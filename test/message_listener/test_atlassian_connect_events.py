# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import json
from datetime import datetime
from ..fixtures.jira_fixtures import *

from polaris.messaging.message_consumer import MessageConsumer
from polaris.messaging.messages import WorkItemsCreated, WorkItemsUpdated
from polaris.messaging.topics import WorkItemsTopic
from polaris.common import db
from unittest.mock import MagicMock

from polaris.utils.token_provider import get_token_provider
from polaris.messaging.test_utils import fake_send, mock_publisher, mock_channel
from polaris.work_tracking.messages import AtlassianConnectWorkItemEvent
from polaris.work_tracking.message_listener import WorkItemsTopicSubscriber
from polaris.work_tracking.integrations.atlassian.jira_work_items_source import JiraProject

mock_consumer = MagicMock(MessageConsumer)
mock_consumer.token_provider = get_token_provider()


def create_issue(project_id, issue_key, issue_id):
    return dict(
        expand="",
        id=issue_id,
        self=f"https://jira.atlassian.com/rest/api/2/issue/{issue_id}",
        key=issue_key,
        fields=dict(
            project=dict(
                self=f"https://jira.atlassian.com/rest/api/2/project/{project_id}",
                id=project_id,
                name="A Project",
                key="PRJ"
            ),
            description=" A new feature",
            summary="A new feature",
            created=datetime.utcnow().isoformat(),
            updated=datetime.utcnow().isoformat(),
            status=dict(
                self="https://jira.atlassian.com/rest/api/2/status/5",
                name="resolved",
                id="5"
            ),
            issuetype=dict(
                self="https://jira.atlassian.com/rest/api/2/issuetype/10000",
                id="10000",
                name="Story"
            )
        )
    )


class TestAtlassianConnectEvent:

    def it_handles_the_issue_created_event(self, jira_work_item_source_fixture, cleanup):
        work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture
        issue_id="10001"
        issue_key=f"PRJ-{issue_id}"

        issue_created = dict(
            timestamp=datetime.utcnow().isoformat(),
            event='issue_created',
            issue=create_issue(jira_project_id, issue_key, issue_id)
        )

        jira_issue_created_message = fake_send(
            AtlassianConnectWorkItemEvent(send=dict(
                atlassian_connector_key=connector_key,
                atlassian_event_type='issue_created',
                atlassian_event=json.dumps(issue_created)
            ))
        )

        publisher = mock_publisher()
        subscriber = WorkItemsTopicSubscriber(mock_channel(), publisher=publisher)
        subscriber.consumer_context = mock_consumer

        message = subscriber.dispatch(mock_channel, jira_issue_created_message)
        assert message
        publisher.assert_topic_called_with_message(WorkItemsTopic, WorkItemsCreated)

        assert db.connection().execute(f"Select count(id) from work_tracking.work_items "
                                       f"where "
                                       f"work_items_source_id={work_items_source.id} "
                                       f"and source_display_id='{issue_key}'").scalar() == 1


    def it_handles_the_issue_updated_event_on_an_existing_issue(self, jira_work_item_source_fixture, cleanup):
        work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture
        issue_id="10001"
        issue_key=f"PRJ-{issue_id}"

        issue = create_issue(jira_project_id, issue_key, issue_id)

        issue_event = dict(
            timestamp=datetime.utcnow().isoformat(),
            event='issue_created',
            issue=issue
        )

        # First create the issue with a message
        jira_issue_created_message = fake_send(
            AtlassianConnectWorkItemEvent(send=dict(
                atlassian_connector_key=connector_key,
                atlassian_event_type='issue_created',
                atlassian_event=json.dumps(issue_event)
            ))
        )

        publisher = mock_publisher()
        subscriber = WorkItemsTopicSubscriber(mock_channel(), publisher=publisher)
        subscriber.consumer_context = mock_consumer

        subscriber.dispatch(mock_channel, jira_issue_created_message)

        jira_issue_updated_message = fake_send(
            AtlassianConnectWorkItemEvent(send=dict(
                atlassian_connector_key=connector_key,
                atlassian_event_type='issue_updated',
                atlassian_event=json.dumps(issue_event)
            ))
        )

        publisher = mock_publisher()
        subscriber = WorkItemsTopicSubscriber(mock_channel(), publisher=publisher)
        subscriber.consumer_context = mock_consumer

        message = subscriber.dispatch(mock_channel, jira_issue_updated_message)
        assert message
        publisher.assert_topic_called_with_message(WorkItemsTopic, WorkItemsUpdated)


    def it_upserts_for_updates(self, jira_work_item_source_fixture, cleanup):
        work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture
        issue_id="10001"
        issue_key=f"PRJ-{issue_id}"

        issue_updated = dict(
            timestamp=datetime.utcnow().isoformat(),
            event='issue_updated',
            issue=create_issue(jira_project_id, issue_key, issue_id)
        )

        jira_issue_created_message = fake_send(
            AtlassianConnectWorkItemEvent(send=dict(
                atlassian_connector_key=connector_key,
                atlassian_event_type='issue_created',
                atlassian_event=json.dumps(issue_updated)
            ))
        )

        publisher = mock_publisher()
        subscriber = WorkItemsTopicSubscriber(mock_channel(), publisher=publisher)
        subscriber.consumer_context = mock_consumer

        message = subscriber.dispatch(mock_channel, jira_issue_created_message)
        assert message
        publisher.assert_topic_called_with_message(WorkItemsTopic, WorkItemsCreated)

        assert db.connection().execute(f"Select count(id) from work_tracking.work_items "
                                       f"where "
                                       f"work_items_source_id={work_items_source.id} "
                                       f"and source_display_id='{issue_key}'").scalar() == 1