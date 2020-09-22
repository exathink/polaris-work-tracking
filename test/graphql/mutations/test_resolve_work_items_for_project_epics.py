# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal

import uuid
import pytest
from unittest.mock import patch
from graphene.test import Client
from unittest.mock import MagicMock

from pika.channel import Channel
from polaris.messaging.message_consumer import MessageConsumer
from polaris.utils.token_provider import get_token_provider

from polaris.common import db
from test.fixtures.jira_fixtures import *
from polaris.utils.collections import Fixture
from polaris.work_tracking.service.graphql import schema
from polaris.work_tracking.db import model
from test.constants import *
from polaris.work_tracking.messages import ResolveWorkItemsForEpic
from polaris.messaging.test_utils import mock_publisher
from polaris.messaging.topics import WorkItemsTopic

mock_channel = MagicMock(Channel)
mock_consumer = MagicMock(MessageConsumer)
mock_consumer.token_provider = get_token_provider()

@pytest.yield_fixture()
def setup_project():
    project = model.Project(
            name='TestProject',
            key=uuid.uuid4(),
            organization_key=polaris_organization_key,
            account_key=exathink_account_key
    )

    yield project
    with db.create_session() as session:
        session.connection.execute("delete from work_tracking.projects")


class TestResolveWorkItemsForProjectEpics:

    @pytest.yield_fixture()
    def setup(self, setup_project):
        project = setup_project

        mutation_statement = """
                mutation resolveWorkItemsForProjectEpics($resolveWorkItemsForProjectEpicsInput: ResolveWorkItemsForProjectEpicsInput!){
                    resolveWorkItemsForProjectEpics(
                        resolveWorkItemsForProjectEpicsInput: $resolveWorkItemsForProjectEpicsInput) {
                        success
                        errorMessage
                    }
                }
                """

        variable_values = dict(
            resolveWorkItemsForProjectEpicsInput=dict(
                projectKey=str(project.key)
            )
        )

        yield Fixture(
            project=project,
            mutation_statement=mutation_statement,
            variable_values=variable_values
        )

    class TestJiraResolveWorkItemsForProjectEpics:

        @pytest.yield_fixture()
        def setup(self, setup, jira_work_items_fixture, cleanup):
            fixture = setup
            work_items, work_items_source, jira_project_id, connector_key = jira_work_items_fixture
            with db.orm_session() as session:
                project = fixture.project
                session.add(project)
                project.work_items_sources.extend([work_items_source])
                session.flush()

            yield Fixture(
                parent=fixture,
                work_items_source=work_items_source,
                work_items=work_items
            )

        class TestPublishMessageToResolveEpicWorkItems:

            def it_publishes_message_to_resolve_epic_work_items_for_each_epic_in_project(self, setup):
                fixture = setup

                client = Client(schema)
                response = client.execute(
                    fixture.mutation_statement,
                    variable_values=fixture.variable_values
                )

                publisher = mock_publisher()
                channel = mock_channel()
                assert response['data']['resolveWorkItemsForProjectEpics']['success']
                publisher.assert_topic_called_with_message(WorkItemsTopic, ResolveWorkItemsForEpic, call=0)




