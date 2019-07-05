# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar
from unittest.mock import patch

from polaris.messaging.test_utils import fake_send, mock_channel, mock_publisher, assert_topic_and_message
from polaris.messaging.messages import ConnectorCreated
from polaris.work_tracking.message_listener import ConnectorsTopicSubscriber

from test.constants import *


class TestConnectorCreated:

    def it_kicks_off_project_fetches_for_pivotal_connector(self, setup_connectors):
        connector_keys = setup_connectors
        message = fake_send(ConnectorCreated(
            send=dict(
                connector_key=connector_keys['pivotal'],
                connector_type='pivotal',
                state='enabled'
            )
        ))

        channel = mock_channel()
        publisher = mock_publisher()

        with patch(
                'polaris.work_tracking.integrations.pivotal_tracker.PivotalTrackerConnector.fetch_work_items_sources_to_sync') as fetch_work_items_sources_to_sync:
            fetch_work_items_sources_to_sync.return_value = []

            ConnectorsTopicSubscriber(channel, publisher=publisher).dispatch(
                channel, message)
            fetch_work_items_sources_to_sync.assert_called()
