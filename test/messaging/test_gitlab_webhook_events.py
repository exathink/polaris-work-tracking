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
    with db.orm_session() as session:
        work_items_sources_keys = [uuid.uuid4() for i in range(0, 1)]
        for key in work_items_sources_keys:
            session.add(
                model.WorkItemsSource(
                    key=key,
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

        project = model.Project(
            name='TestProject',
            key=uuid.uuid4(),
            organization_key=polaris_organization_key,
            account_key=exathink_account_key
        )

        session.add(project)

        session.flush()
        yield project, work_items_sources_keys


class TestGitlabWebhookEvents:
    class TestGitlabIssueEvents:

        @pytest.yield_fixture()
        def setup(self, setup_import_project):
            project, work_items_sources_keys = setup_import_project
