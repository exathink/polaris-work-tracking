# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import json

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from ..fixtures.jira_fixtures import *

from polaris.common import db
from polaris.messaging.message_consumer import MessageConsumer
from polaris.messaging.messages import WorkItemsCreated, WorkItemsUpdated, WorkItemMoved, WorkItemDeleted
from polaris.messaging.test_utils import fake_send, mock_publisher, mock_channel
from polaris.messaging.topics import WorkItemsTopic
from polaris.utils.token_provider import get_token_provider
from polaris.work_tracking.message_listener import WorkItemsTopicSubscriber
from polaris.work_tracking.messages import AtlassianConnectWorkItemEvent

mock_consumer = MagicMock(MessageConsumer)
mock_consumer.token_provider = get_token_provider()


def jira_test_time_stamp():
    # Jira returns timestamps in a local timezone so we need to
    # mock this up here
    return datetime.strftime(datetime.now(tz=timezone(offset=timedelta(hours=-6))), "%Y-%m-%dT%H:%M:%S.%f%z")


def create_issue(project_id, issue_key, issue_id, issue_type='Story', epic_link=None):
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
            created=jira_test_time_stamp(),
            updated=jira_test_time_stamp(),
            status=dict(
                self="https://jira.atlassian.com/rest/api/2/status/5",
                name="resolved",
                id="5"
            ),
            issuetype=dict(
                self="https://jira.atlassian.com/rest/api/2/issuetype/10000",
                id="10000",
                name=issue_type
            ),
            customfield_10014=epic_link,
            components=[
                {
                    "id": "10011",
                    "name": "Jira Integration",
                    "self": "https://exathinkdev.atlassian.net/rest/api/2/component/10011",
                    "description": "Jira Intergration"
                },
                {
                    "id": "10011",
                    "name": "Work Tracking",
                    "self": "https://exathinkdev.atlassian.net/rest/api/2/component/10012",
                    "description": "Work Tracking"
                }
            ]
        )
    )


class TestAtlassianConnectEvent:

    def it_handles_the_issue_created_event(self, jira_work_item_source_fixture, cleanup):
        work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture
        issue_id = "10001"
        issue_key = f"PRJ-{issue_id}"

        issue_created = dict(
            timestamp=jira_test_time_stamp(),
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

    def it_handles_the_issue_created_event_for_issue_created_in_epic(self, jira_work_item_source_fixture, cleanup):
        work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture
        source_epic_id = "10001"
        source_epic_key = f"PRJ-{source_epic_id}"
        issue_type = "Epic"

        # Create an Epic
        issue_created = dict(
            timestamp=jira_test_time_stamp(),
            event='issue_created',
            issue=create_issue(jira_project_id, source_epic_key, source_epic_id, issue_type=issue_type)
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

        parent_id = db.connection().execute(f"Select id from work_tracking.work_items "
                                            f"where "
                                            f"work_items_source_id={work_items_source.id} "
                                            f"and source_display_id='{source_epic_key}' "
                                            f"and is_epic=TRUE ").fetchall()[0][0]
        # create another issue within the above Epic
        issue_id = "10002"
        issue_key = f"PRJ-{issue_id}"
        issue_created = dict(
            timestamp=jira_test_time_stamp(),
            event='issue_created',
            issue=create_issue(jira_project_id, issue_key, issue_id, epic_link=source_epic_key)
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
                                       f"and source_display_id='{issue_key}' "
                                       f"and parent_id={parent_id}").scalar() == 1

    def it_sends_an_update_message_when_an_issue_is_updated_and_app_relevant_fields_change(
            self,
            jira_work_item_source_fixture,
            cleanup
    ):
        work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture
        issue_id = "10001"
        issue_key = f"PRJ-{issue_id}"

        issue = create_issue(jira_project_id, issue_key, issue_id)

        issue_event = dict(
            timestamp=jira_test_time_stamp(),
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

        # make a change to an field that the app cares about
        issue_event['issue']['fields']['summary'] = "Foobar"
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

    def it_does_not_send_an_update_message_when_an_issue_is_updated_but_no_app_relevant_fields_change(
            self,
            jira_work_item_source_fixture,
            cleanup
    ):
        work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture
        issue_id = "10001"
        issue_key = f"PRJ-{issue_id}"

        issue = create_issue(jira_project_id, issue_key, issue_id)

        issue_event = dict(
            timestamp=jira_test_time_stamp(),
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
        assert message is None

    def it_upserts_for_updates(self, jira_work_item_source_fixture, cleanup):
        work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture
        issue_id = "10001"
        issue_key = f"PRJ-{issue_id}"

        issue_updated = dict(
            timestamp=jira_test_time_stamp(),
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

    def it_handles_the_issue_deleted_event(self, jira_work_item_source_fixture, cleanup):
        work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture
        issue_id = "10001"
        issue_key = f"PRJ-{issue_id}"

        issue = create_issue(jira_project_id, issue_key, issue_id)

        issue_event = dict(
            timestamp=jira_test_time_stamp(),
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

        # now delete this issue

        delete_timestamp = datetime.utcnow().isoformat()
        issue_deleted = dict(
            timestamp=delete_timestamp,
            event='issue_deleted',
            issue=issue
        )

        jira_issue_deleted_message = fake_send(
            AtlassianConnectWorkItemEvent(send=dict(
                atlassian_connector_key=connector_key,
                atlassian_event_type='issue_deleted',
                atlassian_event=json.dumps(issue_deleted)
            ))
        )

        publisher = mock_publisher()
        subscriber = WorkItemsTopicSubscriber(mock_channel(), publisher=publisher)
        subscriber.consumer_context = mock_consumer

        message = subscriber.dispatch(mock_channel, jira_issue_deleted_message)
        assert message
        publisher.assert_topic_called_with_message(WorkItemsTopic, WorkItemDeleted)

        # check that the delete date is set
        assert db.connection().execute(f"Select count(id) from work_tracking.work_items "
                                       f"where "
                                       f"work_items_source_id={work_items_source.id} "
                                       f"and source_display_id='{issue_key}' and deleted_at is not NULL").scalar() == 1

    def it_ignores_the_issue_created_event_when_the_work_item_source_is_not_in_check_for_update_import_state(
            self, jira_work_item_source_fixture, cleanup
    ):
        work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture
        issue_id = "10001"
        issue_key = f"PRJ-{issue_id}"

        issue_created = dict(
            timestamp=jira_test_time_stamp(),
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

        db.connection().execute(
            f"update work_tracking.work_items_sources set import_state='disabled' where id={work_items_source.id}"
        )

        publisher = mock_publisher()
        subscriber = WorkItemsTopicSubscriber(mock_channel(), publisher=publisher)
        subscriber.consumer_context = mock_consumer

        message = subscriber.dispatch(mock_channel, jira_issue_created_message)
        assert message is None
        assert db.connection().execute(f"Select count(id) from work_tracking.work_items "
                                       f"where "
                                       f"work_items_source_id={work_items_source.id} "
                                       f"and source_display_id='{issue_key}'").scalar() == 0

    def it_ignores_the_issue_updated_message_when_the_work_items_source_is_not_in_the_check_for_updates_state(
            self,
            jira_work_item_source_fixture,
            cleanup
    ):
        work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture
        issue_id = "10001"
        issue_key = f"PRJ-{issue_id}"

        issue = create_issue(jira_project_id, issue_key, issue_id)

        issue_event = dict(
            timestamp=jira_test_time_stamp(),
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

        # make a change to an field that the app cares about
        issue_event['issue']['fields']['summary'] = "Foobar"
        jira_issue_updated_message = fake_send(
            AtlassianConnectWorkItemEvent(send=dict(
                atlassian_connector_key=connector_key,
                atlassian_event_type='issue_updated',
                atlassian_event=json.dumps(issue_event)
            ))
        )

        db.connection().execute(
            f"update work_tracking.work_items_sources set import_state='disabled' where id={work_items_source.id}"
        )

        publisher = mock_publisher()
        subscriber = WorkItemsTopicSubscriber(mock_channel(), publisher=publisher)
        subscriber.consumer_context = mock_consumer

        message = subscriber.dispatch(mock_channel, jira_issue_updated_message)
        assert message is None

        assert db.connection().execute(f"Select count(id) from work_tracking.work_items "
                                       f"where name='Foobar' and "
                                       f"work_items_source_id={work_items_source.id} "
                                       f"and source_display_id='{issue_key}'").scalar() == 0

    def it_handles_issue_updated_issue_moved_event_when_issue_is_moved_between_existing_work_items_sources(self,
                                                                                                           jira_work_item_source_fixture,
                                                                                                           cleanup):
        work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture
        issue_id = "10001"
        issue_key = f"PRJ-{issue_id}"

        issue = create_issue(jira_project_id, issue_key, issue_id)

        issue_event = dict(
            timestamp=jira_test_time_stamp(),
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

        # create a new work items source
        with db.orm_session() as session:
            session.expire_on_commit = False
            work_items_source = work_tracking.WorkItemsSource(
                key=uuid.uuid4(),
                connector_key=str(connector_key),
                integration_type='jira',
                work_items_source_type=JiraWorkItemSourceType.project.value,
                name='Test Project 2',
                source_id='10002',
                parameters=dict(),
                account_key=account_key,
                organization_key=organization_key,
                commit_mapping_scope='organization',
                import_state=WorkItemsSourceImportState.auto_update.value,
                custom_fields=[{"id": "customfield_10014", "key": "customfield_10014", "name": "Epic Link"}]
            )
            session.add(work_items_source)
            session.flush()

        issue_event['changelog'] = dict(
            items=[
                {
                    "field": "project",
                    "fieldtype": "jira",
                    "fieldId": "project",
                    "from": "10001",
                    "fromString": "test",
                    "to": "10002",
                    "toString": "Test Project 2"
                }
            ]
        )
        issue_event['issue']['key'] = f"PRI-{issue_id}"
        issue_event['issue']['fields']['project']['id'] = '10002'
        issue_event['webhookEvent'] = "jira:issue_updated"
        issue_event['issue_event_type_name'] = "issue_moved"
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
        publisher.assert_topic_called_with_message(WorkItemsTopic, WorkItemMoved)

    def it_handles_issue_updated_issue_moved_event_when_issue_is_moved_between_existing_work_items_sources_target_inactive(
            self, jira_work_item_source_fixture, cleanup):
        work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture
        issue_id = "10001"
        issue_key = f"PRJ-{issue_id}"

        issue = create_issue(jira_project_id, issue_key, issue_id)

        issue_event = dict(
            timestamp=jira_test_time_stamp(),
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

        # create a new work items source
        with db.orm_session() as session:
            session.expire_on_commit = False
            work_items_source = work_tracking.WorkItemsSource(
                key=uuid.uuid4(),
                connector_key=str(connector_key),
                integration_type='jira',
                work_items_source_type=JiraWorkItemSourceType.project.value,
                name='Test Project 2',
                source_id='10002',
                parameters=dict(),
                account_key=account_key,
                organization_key=organization_key,
                commit_mapping_scope='organization',
                import_state=WorkItemsSourceImportState.ready.value,
                custom_fields=[{"id": "customfield_10014", "key": "customfield_10014", "name": "Epic Link"}]
            )
            session.add(work_items_source)
            session.flush()

        issue_event['changelog'] = dict(
            items=[
                {
                    "field": "project",
                    "fieldtype": "jira",
                    "fieldId": "project",
                    "from": "10001",
                    "fromString": "test",
                    "to": "10002",
                    "toString": "Test Project 2"
                }
            ]
        )
        issue_event['issue']['key'] = f"PRI-{issue_id}"
        issue_event['issue']['fields']['project']['id'] = '10002'
        issue_event['webhookEvent'] = "jira:issue_updated"
        issue_event['issue_event_type_name'] = "issue_moved"
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
        publisher.assert_topic_called_with_message(WorkItemsTopic, WorkItemMoved)

    def it_handles_issue_updated_issue_moved_event_when_issue_is_moved_between_existing_work_items_sources_source_inactive(
            self, jira_work_item_source_fixture, cleanup):
        target_work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture

        issue_id = "10001"
        issue_key = f"PRJ-{issue_id}"
        source_jira_project_id = '10002'
        # create a new work items source
        with db.orm_session() as session:
            session.expire_on_commit = False
            source_work_items_source = work_tracking.WorkItemsSource(
                key=uuid.uuid4(),
                connector_key=str(connector_key),
                integration_type='jira',
                work_items_source_type=JiraWorkItemSourceType.project.value,
                name='Test Project 2',
                source_id=source_jira_project_id,
                parameters=dict(),
                account_key=account_key,
                organization_key=organization_key,
                commit_mapping_scope='organization',
                import_state=WorkItemsSourceImportState.ready.value,
                custom_fields=[{"id": "customfield_10014", "key": "customfield_10014", "name": "Epic Link"}]
            )
            session.add(source_work_items_source)
            session.flush()

        issue = create_issue(target_work_items_source.source_id, issue_key, issue_id)

        issue_event = dict(
            timestamp=jira_test_time_stamp(),
            event='issue_updated',
            issue=issue
        )

        issue_event['changelog'] = dict(
            items=[
                {
                    "field": "project",
                    "fieldtype": "jira",
                    "fieldId": "project",
                    "from": source_jira_project_id,
                    "fromString": "Test Project 2",
                    "to": target_work_items_source.source_id,
                    "toString": "test"
                }
            ]
        )
        issue_event['webhookEvent'] = "jira:issue_updated"
        issue_event['issue_event_type_name'] = "issue_moved"
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
        publisher.assert_topic_called_with_message(WorkItemsTopic, WorkItemsCreated)

    def it_handles_issue_updated_issue_moved_event_when_issue_is_moved_from_non_existing_to_active_target_work_items_source(
            self, jira_work_item_source_fixture, cleanup):
        target_work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture

        issue_id = "10001"
        issue_key = f"PRJ-{issue_id}"

        issue = create_issue(target_work_items_source.source_id, issue_key, issue_id)

        issue_event = dict(
            timestamp=jira_test_time_stamp(),
            event='issue_updated',
            issue=issue
        )

        issue_event['changelog'] = dict(
            items=[
                {
                    "field": "project",
                    "fieldtype": "jira",
                    "fieldId": "project",
                    "from": '10002',
                    "fromString": "Test Project 2",
                    "to": target_work_items_source.source_id,
                    "toString": "test"
                }
            ]
        )
        issue_event['webhookEvent'] = "jira:issue_updated"
        issue_event['issue_event_type_name'] = "issue_moved"
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
        publisher.assert_topic_called_with_message(WorkItemsTopic, WorkItemsCreated)

    def it_handles_issue_updated_issue_moved_event_when_issue_is_moved_from_existing_to_non_existing_target_work_items_source(
            self, jira_work_item_source_fixture, cleanup):
        source_work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture

        issue_id = "10001"
        issue_key = f"PRJ-{issue_id}"

        issue = create_issue(jira_project_id, issue_key, issue_id)

        issue_event = dict(
            timestamp=jira_test_time_stamp(),
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

        target_jira_project_id = '10002'
        issue_event['changelog'] = dict(
            items=[
                {
                    "field": "project",
                    "fieldtype": "jira",
                    "fieldId": "project",
                    "from": jira_project_id,
                    "fromString": "test",
                    "to": target_jira_project_id,
                    "toString": "Test Project 2"
                }
            ]
        )
        issue_event['webhookEvent'] = "jira:issue_updated"
        issue_event['issue_event_type_name'] = "issue_moved"
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
        publisher.assert_topic_called_with_message(WorkItemsTopic, WorkItemMoved)
