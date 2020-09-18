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

from polaris.common import db
from test.fixtures.jira_fixtures import *
from polaris.utils.collections import Fixture
from polaris.work_tracking.service.graphql import schema


class TestUpdateWorkItemsSourceCustomFields:

    @pytest.yield_fixture
    def setup(self):
        mutation_statement = """
        mutation updateWorkItemsSourceCustomFields($updateWorkItemsSourceCustomFieldsInput: UpdateWorkItemsSourceCustomFieldsInput!){
            updateWorkItemsSourceCustomFields(
                updateWorkItemsSourceCustomFieldsInput: $updateWorkItemsSourceCustomFieldsInput) {
                success
                errorMessage
            }
        }
        """
        custom_fields = [
            dict(
                name='Epic Link',
                id='customfield_10014',
                key='customfield_10014'
            )
        ]

        yield Fixture(
            mutation_statement=mutation_statement,
            custom_fields=custom_fields
        )

    class TestJiraUpdateWorkItemsSourceCustomFields:

        @pytest.yield_fixture()
        def setup(self, setup, jira_work_item_source_fixture, cleanup):
            fixture = setup
            work_items_source, _, _ = jira_work_item_source_fixture
            yield Fixture(
                parent=fixture,
                work_items_source=work_items_source
            )

        class TestWhenWorkItemsSourceExists:

            def it_imports_custom_fields(self, setup):
                fixture = setup
                client = Client(schema)
                with patch(
                        'polaris.work_tracking.integrations.atlassian.jira_connector.JiraConnector.fetch_custom_fields') as fetch_custom_fields:
                    fetch_custom_fields.return_value = fixture.custom_fields
                    response = client.execute(
                        fixture.mutation_statement,
                        variable_values=dict(
                            updateWorkItemsSourceCustomFieldsInput=dict(
                                workItemsSources=[
                                    dict(
                                        workItemsSourceKey=str(fixture.work_items_source.key)
                                    )
                                ]
                            )
                        ))
                    assert response['data']['updateWorkItemsSourceCustomFields']['success']
                assert db.connection().execute(
                    f"select custom_fields from work_tracking.work_items_sources where key='{fixture.work_items_source.key}'").fetchall()[
                           0][0] == fetch_custom_fields.return_value

        class TestWhenWorkItemsSourceDoesNotExist:

            def it_does_not_import_but_returns_message_work_items_source_not_available_for_this_import(self, setup):
                fixture = setup
                work_items_source_key = uuid.uuid4()
                client = Client(schema)
                with patch(
                        'polaris.work_tracking.integrations.atlassian.jira_connector.JiraConnector.fetch_custom_fields') as fetch_custom_fields:
                    fetch_custom_fields.return_value = fixture.custom_fields
                    response = client.execute(fixture.mutation_statement, variable_values=dict(
                        updateWorkItemsSourceCustomFieldsInput=dict(
                            workItemsSources=[dict(workItemsSourceKey=str(work_items_source_key))])))
                    assert not response['data']['updateWorkItemsSourceCustomFields']['success']
                    assert response['data']['updateWorkItemsSourceCustomFields'][
                               'errorMessage'] == f"Work Item source with key: {work_items_source_key} not available for this import"

        class TestWhenInputKeyDoesNotMatchUUIDFormat:

            def it_returns_failure_message(self, setup):
                fixture = setup
                work_items_source_key = "1234"
                client = Client(schema)
                with patch(
                        'polaris.work_tracking.integrations.atlassian.jira_connector.JiraConnector.fetch_custom_fields') as fetch_custom_fields:
                    fetch_custom_fields.return_value = fixture.custom_fields
                    response = client.execute(
                        fixture.mutation_statement,
                        variable_values=dict(
                            updateWorkItemsSourceCustomFieldsInput=dict(
                                workItemsSources=[
                                    dict(
                                        workItemsSourceKey=str(work_items_source_key)
                                    )
                                ]
                            )
                        ))
                    assert not response['data']['updateWorkItemsSourceCustomFields']['success']
                    assert response['data']['updateWorkItemsSourceCustomFields'][
                               'errorMessage'] == f"Import project custom fields failed"

    class TestNonJiraCustomFieldsImport:

        @pytest.yield_fixture
        def setup(self, setup, setup_work_item_sources, cleanup):
            fixture = setup
            _, work_items_sources = setup_work_item_sources
            yield Fixture(
                parent=fixture,
                pivotal_source=work_items_sources['pivotal'],
                github_source=work_items_sources['github']
            )

        class TestPivotalCustomFieldsImport:

            def it_does_not_import_but_returns_message_work_items_source_not_available_for_this_import(self, setup):
                fixture = setup
                work_items_source_key = fixture.pivotal_source.key
                client = Client(schema)
                with patch(
                        'polaris.work_tracking.integrations.atlassian.jira_connector.JiraConnector.fetch_custom_fields') as fetch_custom_fields:
                    fetch_custom_fields.return_value = fixture.custom_fields
                    response = client.execute(
                        fixture.mutation_statement,
                        variable_values=dict(
                            updateWorkItemsSourceCustomFieldsInput=dict(
                                workItemsSources=[
                                    dict(
                                        workItemsSourceKey=str(work_items_source_key)
                                    )
                                ]
                            )
                        ))
                    assert not response['data']['updateWorkItemsSourceCustomFields']['success']
                    assert response['data']['updateWorkItemsSourceCustomFields'][
                               'errorMessage'] == f"Work Item source with key: {work_items_source_key} not available for this import"

        class TestGithubCustomFieldsImport:

            def it_does_not_import_but_returns_message_work_items_source_not_available_for_this_import(self, setup):
                fixture = setup
                work_items_source_key = fixture.github_source.key
                client = Client(schema)
                with patch(
                        'polaris.work_tracking.integrations.atlassian.jira_connector.JiraConnector.fetch_custom_fields') as fetch_custom_fields:
                    fetch_custom_fields.return_value = fixture.custom_fields
                    response = client.execute(
                        fixture.mutation_statement,
                        variable_values=dict(
                            updateWorkItemsSourceCustomFieldsInput=dict(
                                workItemsSources=[
                                    dict(
                                        workItemsSourceKey=str(work_items_source_key)
                                    )
                                ]
                            )
                        ))
                    assert not response['data']['updateWorkItemsSourceCustomFields']['success']
                    assert response['data']['updateWorkItemsSourceCustomFields'][
                               'errorMessage'] == f"Work Item source with key: {work_items_source_key} not available for this import"
