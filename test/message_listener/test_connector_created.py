# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar
import pytest
import uuid
from polaris.messaging.test_utils import fake_send, mock_channel, mock_publisher, assert_topic_and_message
from polaris.messaging.topics import ConnectorsTopic
from polaris.messaging.messages import ConnectorCreated
from polaris.work_tracking.message_listener import ConnectorsTopicSubscriber
from polaris.common import db
from polaris.integrations.db.model import PivotalTracker

from test.constants import *

pivotal_connector_key = uuid.uuid4()


@pytest.yield_fixture
def connectors():
    yield [
        PivotalTracker(
            name='pivotal test',
            base_url='https://www.pivotaltracker.com',
            api_key='foo',
            key=pivotal_connector_key
        )
    ]

@pytest.fixture
def setup_connectors(connectors):
    with db.orm_session() as session:
        for connector in connectors:
            session.add(connector)



class TestConnectorCreated:

    def it_kicks_off_project_fetches_for_pivotal_connector(self, setup_connectors):
        message = fake_send(ConnectorCreated(
            send=dict(
                connector_key=pivotal_connector_key,
                connector_type='pivotal',
                state='enabled'
            )
        ))

        channel = mock_channel()
        publisher = mock_publisher()

        created_messages, updated_messages = ConnectorsTopicSubscriber(channel, publisher=publisher).dispatch(channel, message)
        assert len(created_messages) == 0
        assert len(updated_messages) == 0