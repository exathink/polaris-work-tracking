# -*- coding: utf-8 -*-

#  Copyright (c) Exathink, LLC  2016-2023.
#  All rights reserved
#

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar
import json
from unittest.mock import MagicMock

import pkg_resources
from pika.channel import Channel

from polaris.messaging.message_consumer import MessageConsumer
from polaris.messaging.messages import WorkItemsUpdated
from polaris.messaging.test_utils import mock_publisher, mock_channel, assert_topic_and_message, fake_send
from polaris.messaging.topics import WorkItemsTopic
from polaris.utils.token_provider import get_token_provider
from polaris.work_tracking import commands
from polaris.work_tracking.db import api
from polaris.work_tracking.integrations.atlassian.jira_work_items_source import JiraProject
from polaris.work_tracking.message_listener import WorkItemsTopicSubscriber
from polaris.work_tracking.messages import CustomTagMappingChanged
from polaris.utils.collections import find
from ..fixtures.jira_fixtures import *

mock_channel = MagicMock(Channel)
mock_consumer = MagicMock(MessageConsumer)
mock_consumer.token_provider = get_token_provider()


class TestCustomTagMappingChanged(WorkItemsSourceTest):
    """
    The setup here is a work item source with an
    existing set of work items that have an api_payload.
    We will initially import the work items with no parent path
    selectors set in the work items source.

    Then we will update the parent path selectors in the work items source
    and then publish the message.

    The message processor will process all the work items in the work item source
    (paging as necessary), and process the current api_payload as though it was a new message.

    Doing so, it will update the parent keys of any work items that have had a new parent key mapped
    via the parent key selector, and then publish these work items as updates to the analytics service.

    We should see both an updated parent key in the local database, and a WorkItemsUpdated message published
    for the updated items, and only the updated items to the WorkItemsTopic so that it can be processed by the Analytocs Listener.

    In implementing this we should be able to use all the existing machinery for processing an update to the work items source.


    """

    class TestMessageListener:
        @pytest.fixture()
        def setup(self, setup):
            fixture = setup
            work_items_source = fixture.work_items_source
            issue_templates = [
                json.loads(
                    pkg_resources.resource_string(__name__, data_file)
                )
                for data_file in [
                    '../data/jira_payload_with_feature_parent.json',
                    '../data/jira_payload_for_custom_parent.json',
                    '../data/jira_payload_with_components.json'
                ]
            ]

            with db.orm_session() as session:
                session.add(work_items_source)
                project = JiraProject(work_items_source)

            yield Fixture(
                organization_key=organization_key,
                project=project,
                work_items_source=work_items_source,
                connector_key=work_items_source.connector_key,
                issue_templates=issue_templates,
                issue_with_feature_parent=issue_templates[0],

            )

        class TestTagReprocessing:

            def it_reproceses_the_work_items_and_detects_work_items_with_changed_tags(self, setup):
                fixture = setup
                project = fixture.project
                work_items_source = fixture.work_items_source
                target_issue = fixture.issue_with_feature_parent

                # Load the parent and child issue.
                work_item_summaries = [
                    project.map_issue_to_work_item_data(issue)
                    for issue in fixture.issue_templates
                ]

                #
                api.sync_work_items(work_items_source.key, work_item_summaries)

                # Now add a parent path selector to the work item source. When we reprocess, this should
                # reset the parent source id and link to the new parent.
                with db.orm_session() as session:
                    session.add(work_items_source)
                    # set to the selector for any ch
                    work_items_source.parameters = dict(
                        custom_tag_mapping=[
                            dict(
                                mapping_type='path-selector',
                                selector="((fields.issuelinks[?type.name=='Parent/Child'])[?outwardIssue.fields.issuetype.name == 'Feature'])[0]",
                                tag="feature-item"
                            )
                        ]
                    )
                # reprocess the work items
                for items in commands.reprocess_work_items(work_items_source.key,
                                                                       attributes_to_check=['tags'],
                                                                       batch_size=100):
                    assert len(items) == 1







        @pytest.mark.skip
        class TestMessagePublishing:

            def it_processes_the_message_from_end_to_end_for_a_single_work_item_with_a_change(self, setup):
                fixture = setup
                organization_key = fixture.organization_key
                work_items_source = fixture.work_items_source

                issue_template = fixture.issue_with_custom_parent
                work_item_summaries = [fixture.project.map_issue_to_work_item_data(issue_template)]
                # create a single work item without a parent path selector on the work item source
                api.sync_work_items(work_items_source.key, work_item_summaries)

                with db.orm_session() as session:
                    session.add(work_items_source)
                    work_items_source.parameters = dict(
                        parent_path_selectors=[
                            "(fields.issuelinks[?type.name=='Parent/Child'].outwardIssue.key)[0]"
                        ]
                    )

                message = fake_send(
                    CustomTagMappingChanged(send=dict(
                        organization_key=organization_key,
                        work_items_source_key=work_items_source.key
                    ))
                )
                publisher = mock_publisher()
                subscriber = WorkItemsTopicSubscriber(mock_channel, publisher=publisher)
                subscriber.consumer_context = mock_consumer

                messages = subscriber.dispatch(mock_channel, message)
                assert len(messages) == 1

                publisher.assert_topic_called_with_message(WorkItemsTopic, WorkItemsUpdated, call_count=1)


            def it_does_not_publish_a_message_when_there_are_no_changes(self, setup):
                fixture = setup
                organization_key = fixture.organization_key
                work_items_source = fixture.work_items_source

                issue_template = fixture.issue_with_custom_parent
                work_item_summaries = [fixture.project.map_issue_to_work_item_data(issue_template)]
                # create a single work item without a parent path selector on the work item source
                api.sync_work_items(work_items_source.key, work_item_summaries)


                message = fake_send(
                    CustomTagMappingChanged(send=dict(
                        organization_key=organization_key,
                        work_items_source_key=work_items_source.key
                    ))
                )
                publisher = mock_publisher()
                subscriber = WorkItemsTopicSubscriber(mock_channel, publisher=publisher)
                subscriber.consumer_context = mock_consumer

                messages = subscriber.dispatch(mock_channel, message)
                assert len(messages) == 0
                publisher.assert_not_called()