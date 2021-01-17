# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal

import uuid
import pytest
from unittest.mock import patch
from test.constants import *
from polaris.utils.collections import Fixture
from graphene.test import Client
from polaris.work_tracking.service.graphql import schema
from polaris.common import db


class TestRegisterWorkItemsSourceConnectorWebhooks:
    class TestWithGitlabConnector:

        @pytest.yield_fixture()
        def setup(self, setup_work_item_sources, cleanup):
            session, work_items_sources = setup_work_item_sources
            session.commit()
            gitlab_work_items_source_key = work_items_sources['gitlab'].key
            connector_key = work_items_sources['gitlab'].connector_key
            active_hook_id = '1000'
            registered_events = ['issues_events']
            mutation_string = """
                mutation registerWorkItemsSourceConnectorWebhooks($registerWebhooksInput: RegisterWebhooksInput!) {
                    registerWorkItemsSourceConnectorWebhooks(registerWebhooksInput: $registerWebhooksInput){
                    webhooksRegistrationStatus {
                      workItemsSourceKey
                      success
                      message
                    }
                  }
                }
            """
            yield Fixture(
                organization_key=polaris_organization_key,
                work_items_source_key=gitlab_work_items_source_key,
                connector_key=connector_key,
                mutation_string=mutation_string,
                registered_events=registered_events,
                active_hook_id=active_hook_id
            )

        def it_registers_new_webhook_and_updates_info(self, setup):
            fixture = setup
            client = Client(schema)

            with patch(
                    'polaris.work_tracking.integrations.gitlab.GitlabWorkTrackingConnector.register_project_webhooks'
            ) as register_webhooks:
                register_webhooks.return_value = dict(
                    success=True,
                    active_webhook=fixture.active_hook_id,
                    deleted_webhooks=[],
                    registered_events=fixture.registered_events
                )
                response = client.execute(
                    fixture.mutation_string,
                    variable_values=dict(
                        registerWebhooksInput=dict(
                            connectorKey=str(fixture.connector_key),
                            workItemsSourceKeys=[str(fixture.work_items_source_key)]
                        )
                    )
                )
                assert 'data' in response
                status = response['data']['registerWorkItemsSourceConnectorWebhooks']['webhooksRegistrationStatus']
                assert len(status) == 1
                assert status[0]['success']

                assert db.connection().execute(
                    f"select count(*) from work_tracking.work_items_sources \
                    where key='{fixture.work_items_source_key}' \
                    and source_data->>'active_webhook'='{fixture.active_hook_id}'" \
                    ).scalar() == 1

        def it_re_registers_webhooks_and_updates_source_data(self, setup):
            fixture = setup
            client = Client(schema)
            new_webhook_id = 1001

            with patch(
                    'polaris.work_tracking.integrations.gitlab.GitlabWorkTrackingConnector.register_project_webhooks'
            ) as register_webhooks:
                register_webhooks.return_value = dict(
                    success=True,
                    active_webhook=fixture.active_hook_id,
                    deleted_webhooks=[],
                    registered_events=fixture.registered_events
                )
                response = client.execute(
                    fixture.mutation_string,
                    variable_values=dict(
                        registerWebhooksInput=dict(
                            connectorKey=str(fixture.connector_key),
                            workItemsSourceKeys=[str(fixture.work_items_source_key)]
                        )
                    )
                )
                assert 'data' in response
                status = response['data']['registerWorkItemsSourceConnectorWebhooks']['webhooksRegistrationStatus']
                assert len(status) == 1
                assert status[0]['success']

                assert db.connection().execute(
                    f"select count(*) from work_tracking.work_items_sources \
                    where key='{fixture.work_items_source_key}' \
                    and source_data->>'active_webhook'='{fixture.active_hook_id}'" \
                    ).scalar() == 1

            with patch(
                    'polaris.work_tracking.integrations.gitlab.GitlabWorkTrackingConnector.register_project_webhooks'
            ) as register_webhooks:
                register_webhooks.return_value = dict(
                    success=True,
                    active_webhook=new_webhook_id,
                    deleted_webhooks=[fixture.active_hook_id],
                    registered_events=fixture.registered_events
                )
                response = client.execute(
                    fixture.mutation_string,
                    variable_values=dict(
                        registerWebhooksInput=dict(
                            connectorKey=str(fixture.connector_key),
                            workItemsSourceKeys=[str(fixture.work_items_source_key)]
                        )
                    )
                )
                assert 'data' in response
                status = response['data']['registerWorkItemsSourceConnectorWebhooks']['webhooksRegistrationStatus']
                assert len(status) == 1
                assert status[0]['success']

                assert db.connection().execute(
                    f"select count(*) from work_tracking.work_items_sources \
                    where key='{fixture.work_items_source_key}' \
                    and source_data->>'active_webhook'='{new_webhook_id}' \
                    and source_data->>'inactive_webhooks'='[]'" \
                    ).scalar() == 1

        def it_returns_connector_not_found_when_connector_id_is_incorrect(self, setup):
            fixture = setup
            client = Client(schema)
            test_connector_key = str(uuid.uuid4())
            with patch(
                    'polaris.work_tracking.integrations.gitlab.GitlabWorkTrackingConnector.register_project_webhooks'
            ) as register_webhooks:
                register_webhooks.return_value = dict(
                    success=True,
                    active_webhook=fixture.active_hook_id,
                    deleted_webhooks=[],
                    registered_events=fixture.registered_events
                )
                response = client.execute(
                    fixture.mutation_string,
                    variable_values=dict(
                        registerWebhooksInput=dict(
                            connectorKey=str(test_connector_key),
                            workItemsSourceKeys=[str(fixture.work_items_source_key)]
                        )
                    )
                )
                assert 'data' in response
                status = response['data']['registerWorkItemsSourceConnectorWebhooks']['webhooksRegistrationStatus']
                assert len(status) == 1
                assert not status[0]['success']
                assert status[0][
                           'message'] == f"Register webhooks failed due to: Cannot find connector for connector_key {test_connector_key}"
