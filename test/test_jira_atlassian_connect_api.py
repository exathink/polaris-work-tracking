# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import json
from unittest.mock import patch

from atlassian_jwt import encode_token

from .fixtures.jira_fixtures import *


class TestJiraAtlassianConnectApi:

    def it_handles_the_issue_created_webhook(self, app_fixture):
        app, client, connector_key = app_fixture
        url = '/atlassian_connect/webhook/jiraissue_created'
        token = encode_token(
            'POST',
            url,
            client_key,
            shared_secret
        )
        json_payload = {**payload, **dict(eventType="jira:issue_created")}
        with patch('polaris.work_tracking.integrations.atlassian.jira_atlassian_connect.publish') as publish:
            response = client.post(
                url,
                json=json_payload,
                headers=dict(authorization=f"JWT {token}")
            )
            assert response.status_code == 204
            publish.atlassian_connect_work_item_event.assert_called()
            call_args = publish.atlassian_connect_work_item_event.call_args[1]

            assert call_args['atlassian_connector_key'] == connector_key
            assert call_args['atlassian_event_type'] == 'issue_created'
            assert json.loads(call_args['atlassian_event']) == json_payload

    def it_handles_the_issue_updated_webhook(self, app_fixture):
        app, client, connector_key = app_fixture
        url = '/atlassian_connect/webhook/jiraissue_updated'
        token = encode_token(
            'POST',
            url,
            client_key,
            shared_secret
        )
        json_payload = {**payload, **dict(eventType="jira:issue_updated")}
        with patch('polaris.work_tracking.integrations.atlassian.jira_atlassian_connect.publish') as publish:
            response = client.post(
                url,
                json=json_payload,
                headers=dict(authorization=f"JWT {token}")
            )
            assert response.status_code == 204
            publish.atlassian_connect_work_item_event.assert_called()
            call_args = publish.atlassian_connect_work_item_event.call_args[1]

            assert call_args['atlassian_connector_key'] == connector_key
            assert call_args['atlassian_event_type'] == 'issue_updated'
            assert json.loads(call_args['atlassian_event']) == json_payload

    def it_handles_the_issue_deleted_webhook(self, app_fixture):
        app, client, connector_key = app_fixture
        url = '/atlassian_connect/webhook/jiraissue_deleted'
        token = encode_token(
            'POST',
            url,
            client_key,
            shared_secret
        )
        json_payload = {**payload, **dict(eventType="jira:issue_deleted")}
        with patch('polaris.work_tracking.integrations.atlassian.jira_atlassian_connect.publish') as publish:
            response = client.post(
                url,
                json=json_payload,
                headers=dict(authorization=f"JWT {token}")
            )
            assert response.status_code == 204
            publish.atlassian_connect_work_item_event.assert_called()
            call_args = publish.atlassian_connect_work_item_event.call_args[1]

            assert call_args['atlassian_connector_key'] == connector_key
            assert call_args['atlassian_event_type'] == 'issue_deleted'
            assert json.loads(call_args['atlassian_event']) == json_payload


