# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar


import uuid

import pytest
from flask import Flask

from polaris.common import db
from polaris.common.enums import JiraWorkItemSourceType
from polaris.integrations.db import model as integrations
from polaris.integrations.db.api import load_atlassian_connect_record
from polaris.work_tracking.db import model as work_tracking
from polaris.work_tracking.integrations.atlassian import jira_atlassian_connect

key = uuid.uuid4().hex
client_key = uuid.uuid4().hex
shared_secret = 'my deep dark secret'
public_key = uuid.uuid4().hex

account_key = uuid.uuid4().hex
organization_key = uuid.uuid4().hex

payload = dict(
    key='polaris.jira',
    clientKey=client_key,
    sharedSecret=shared_secret,
    publicKey=public_key,
    serverVersion='1.0',
    pluginsVersion='1.0',
    baseUrl='https://exathinkdev.atlassian.net',
    productType='jira',
    description='Its JIRA dude..',
    serviceEntitlementNumber='42'
)

@pytest.fixture(scope='module')
def setup_integrations_schema(db_up):
    integrations.recreate_all(db.engine())

@pytest.fixture(scope='module')
def setup_work_tracking_schema(db_up):
    work_tracking.recreate_all(db.engine())


@pytest.yield_fixture
def app_fixture(setup_integrations_schema):
    app = Flask(__name__)
    app.testing = True
    client = app.test_client()

    jira_atlassian_connect.init_connector(app)

    # Install the app
    response = client.post(
        '/atlassian_connect/lifecycle/installed',
        json={**payload, **dict(eventType="installed")}
    )
    assert response.status_code == 204

    connector = load_atlassian_connect_record(client_key)

    yield app, client, connector.key


@pytest.yield_fixture
def jira_work_item_source_fixture(app_fixture, setup_work_tracking_schema):
    _, _,  connector_key = app_fixture
    jira_project_id = "10001"
    with db.orm_session() as session:
        work_items_source = work_tracking.WorkItemsSource(
            key=uuid.uuid4(),
            connector_key=str(connector_key),
            integration_type='jira',
            work_items_source_type=JiraWorkItemSourceType.project.value,
            name='test',
            source_id=jira_project_id,
            parameters=dict(),
            account_key=account_key,
            organization_key=organization_key,
            commit_mapping_scope='organization'
        )
        session.add(work_items_source)

    yield work_items_source, jira_project_id, connector_key


@pytest.yield_fixture
def cleanup():

    yield

    with db.create_session() as session:
        session.connection.execute("delete from work_tracking.work_items")
        session.connection.execute("delete from integrations.atlassian_connect")
        session.connection.execute("delete from integrations.connectors")
