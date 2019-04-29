# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar
import pytest
import json
from flask import Flask
from unittest.mock import patch
import uuid
from atlassian_jwt import encode_token
from polaris.integrations.db.api import load_atlassian_connect_record
from polaris.work_tracking.service.atlassian import jira
from polaris.common import db
from polaris.integrations.db import model

key = uuid.uuid4().hex
client_key = uuid.uuid4().hex
shared_secret = 'my deep dark secret'
public_key = uuid.uuid4().hex


payload = dict(
    key='polaris.jira',
    clientKey=client_key,
    sharedSecret=shared_secret,
    publicKey=public_key,
    serverVersion='1.0',
    pluginsVersion='1.0',
    baseUrl='https://exathinkdev.atlassian.net',
    productType='JIRA',
    description='Its JIRA dude..',
    serviceEntitlementNumber='42'
)

@pytest.fixture(scope='module')
def setup_integrations_schema(db_up):
    model.recreate_all(db.engine())

@pytest.yield_fixture
def app_fixture(setup_integrations_schema):
    app = Flask(__name__)
    app.testing = True
    client = app.test_client()

    jira.init_connector(app)

    # Install the app
    response = client.post(
        '/atlassian_connect/lifecycle/installed',
        json={**payload, **dict(eventType="installed")}
    )
    assert response.status_code == 204

    connector = load_atlassian_connect_record(client_key)

    yield app, client, connector.key


class TestJiraConnector:

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
        with patch('polaris.work_tracking.service.atlassian.jira.publish') as publish:
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
