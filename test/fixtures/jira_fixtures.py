# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar


import uuid

import pytest
from flask import Flask
from datetime import datetime
from unittest.mock import patch
from polaris.common import db
from polaris.utils.collections import Fixture
from polaris.common.enums import JiraWorkItemSourceType, WorkItemsSourceImportState
from polaris.integrations.db import model as integrations
from polaris.integrations.db.api import load_atlassian_connect_record
from polaris.work_tracking.db import model as work_tracking
from polaris.work_tracking.integrations.atlassian import jira_atlassian_connect
from polaris.common.enums import JiraWorkItemType

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


@pytest.fixture
def app_fixture(setup_integrations_schema):
    app = Flask(__name__)
    app.testing = True
    client = app.test_client()

    jira_atlassian_connect.init_connector(app)

    # Install the app - turning off install signature verification here since
    # it is not relevant to this the actual functional tests for the connector.
    with patch('polaris.integrations.atlassian_connect.atlassian_connect_verify_install_signature'):
        response = client.post(
            '/atlassian_connect/lifecycle/installed',
            json={**payload, **dict(eventType="installed")}
        )
        assert response.status_code == 204

    connector = load_atlassian_connect_record(client_key)

    yield app, client, connector.key


@pytest.fixture
def jira_work_item_source_fixture(setup_work_tracking_schema, app_fixture):
    _, _, connector_key = app_fixture
    jira_project_id = "10001"
    with db.orm_session() as session:
        session.expire_on_commit = False
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
            commit_mapping_scope='organization',
            import_state=WorkItemsSourceImportState.auto_update.value,
            custom_fields=[{"id": "customfield_10014", "key": "customfield_10014", "name": "Epic Link"},
                           {"id": "customfield_10029", "key": "customfield_10029", "name": "Story Points",
                            "custom": True, "schema": {"type": "number",
                                                       "custom": "com.atlassian.jira.plugin.system.customfieldtypes:float",
                                                       "customId": 10029}},
                           {"id": "customfield_10016", "key": "customfield_10016", "name": "Story point estimate",
                            "custom": True,
                            "schema": {"type": "number", "custom": "com.pyxis.greenhopper.jira:jsw-story-points",
                                       "customId": 10016}}, {
                               "id": "customfield_10007",
                               "key": "customfield_10007",
                               "name": "Sprint",
                               "custom": True,
                               "schema": {
                                   "type": "array",
                                   "items": "json",
                                   "custom": "com.pyxis.greenhopper.jira:gh-sprint",
                                   "customId": 10007
                               },
                               "navigable": True,
                               "orderable": True,
                               "searchable": True,
                               "clauseNames": [
                                   "cf[10007]",
                                   "Sprint"
                               ],
                               "untranslatedName": "Sprint"
                           },
                           {"id": "customfield_10030", "key": "customfield_10030", "name": "Flagged", "custom": True,
                            "schema": {"type": "array", "items": "option",
                                       "custom": "com.atlassian.jira.plugin.system.customfieldtypes:multicheckboxes",
                                       "customId": 10030},
                            "navigable": True, "orderable": True, "searchable": True,
                            "clauseNames": ["cf[10030]", "Flagged", "Flagged[Checkboxes]"],
                            "untranslatedName": "Flagged"}
                           ]
        )
        session.add(work_items_source)
        session.flush()

    yield work_items_source, jira_project_id, connector_key


@pytest.fixture
def jira_work_item_source_with_multiple_story_points_fixture(setup_work_tracking_schema, app_fixture):
    _, _, connector_key = app_fixture
    jira_project_id = "10001"
    with db.orm_session() as session:
        session.expire_on_commit = False
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
            commit_mapping_scope='organization',
            import_state=WorkItemsSourceImportState.auto_update.value,
            custom_fields=[{"id": "customfield_10014", "key": "customfield_10014", "name": "Epic Link"},
                           {"id": "customfield_11563", "key": "customfield_11563", "name": "Story Points",
                            "custom": True,
                            "schema": {"type": "number",
                                       "custom": "com.atlassian.jira.plugin.system.customfieldtypes:float",
                                       "customId": 11563}},
                           {"id": "customfield_10011", "key": "customfield_10011", "name": "Story Points",
                            "custom": True,
                            "schema": {"type": "number",
                                       "custom": "com.atlassian.jira.plugin.system.customfieldtypes:float",
                                       "customId": 10011}},
                           {"id": "customfield_10016", "key": "customfield_10016", "name": "Story point estimate",
                            "custom": True,
                            "schema": {"type": "number", "custom": "com.pyxis.greenhopper.jira:jsw-story-points",
                                       "customId": 10016}}]
        )
        session.add(work_items_source)
        session.flush()

    yield work_items_source, jira_project_id, connector_key


class WorkItemsSourceTest:
    @pytest.fixture()
    def setup(self, jira_work_item_source_fixture, cleanup):
        work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture
        yield Fixture(
            work_items_source=work_items_source,
            project_id=jira_project_id,
            connector_key=connector_key,
            organization_key=organization_key
        )


def setup_jira_work_items(work_items_source):
    for display_id in range(1000, 1010):
        work_items_source.work_items.append(
            work_tracking.WorkItem(
                key=uuid.uuid4(),
                name=f"Issue {display_id}",
                description="An issue in detail",
                work_item_type=JiraWorkItemType.task.value,
                is_bug=False,
                is_epic=False,
                tags=[],
                source_id=str(display_id),
                source_display_id=str(display_id),
                source_state='',
                url='',
                source_created_at=datetime.utcnow(),
                source_last_updated=datetime.utcnow(),
                last_sync=datetime.utcnow(),
                parent_id=None
            )
        )
    # add an epic
    display_id = 1011
    work_items_source.work_items.append(
        work_tracking.WorkItem(
            key=uuid.uuid4(),
            name=f"Issue {display_id}",
            description="An issue in detail",
            work_item_type=JiraWorkItemType.epic.value,
            is_bug=False,
            is_epic=True,
            tags=[],
            source_id=str(display_id),
            source_display_id=str(display_id),
            source_state='',
            url='',
            source_created_at=datetime.utcnow(),
            source_last_updated=datetime.utcnow(),
            last_sync=datetime.utcnow(),
            parent_id=None
        )
    )

    return work_items_source.work_items


@pytest.fixture()
def jira_work_items_fixture(jira_work_item_source_fixture):
    work_items_source, jira_project_id, connector_key = jira_work_item_source_fixture
    work_items = []
    with db.orm_session() as session:
        session.add(work_items_source)
        work_items.extend(setup_jira_work_items(work_items_source))
        session.flush()

    yield work_items, work_items_source, jira_project_id, connector_key


@pytest.fixture
def cleanup():
    yield

    with db.create_session() as session:
        session.connection.execute("delete from work_tracking.work_items")
        session.connection.execute("delete from work_tracking.work_items_sources")

        session.connection.execute("delete from integrations.atlassian_connect")
        session.connection.execute("delete from integrations.connectors")
