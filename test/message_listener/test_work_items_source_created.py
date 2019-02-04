# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import uuid
from polaris.messaging.test_utils import fake_send, mock_channel, mock_publisher, assert_topic_and_message
from polaris.messaging.topics import WorkItemsTopic
from polaris.messaging.messages import WorkItemsSourceCreated, ImportWorkItems
from polaris.work_tracking.message_listener import WorkItemsTopicSubscriber

from test.constants import *

class TestWorkItemsSourceCreated:

    def it_kicks_off_an_import_for_the_work_items_source(self):
        message = fake_send(WorkItemsSourceCreated(
            send=dict(
                organization_key=rails_organization_key,
                work_items_source=dict(
                    key=uuid.uuid4(),
                    name='foo',
                    integration_type='github',
                    commit_mapping_scope='organization',
                    commit_mapping_scope_key=rails_organization_key
                )
            )
        ))

        channel = mock_channel()
        publisher = mock_publisher()

        WorkItemsTopicSubscriber(channel, publisher=publisher).dispatch(channel, message)
        publisher.assert_topic_called_with_message(WorkItemsTopic, ImportWorkItems)