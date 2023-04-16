# -*- coding: utf-8 -*-

#  Copyright (c) Exathink, LLC  2016-2023.
#  All rights reserved
#

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import pytest
from unittest.mock import patch
from graphene.test import Client
from polaris.common import db
from polaris.work_tracking.db.model import WorkItemsSource
from polaris.work_tracking.service.graphql import schema

from test.fixtures.jira_fixtures import *


class TestUpdateWorkItemsSourceParameters(WorkItemsSourceTest):
    class TestUpdateParameters:

        def it_creates_the_parameters_for_the_first_time(self, setup):
            fixture = setup
            work_items_source = fixture.work_items_source
            connector_key = fixture.connector_key

            client = Client(schema)
            mutation = """
                mutation updateWorkItemsSourceParameters(
                    $updateWorkItemsSourceParametersInput: UpdateWorkItemsSourceParametersInput! 
                    ) {
                        updateWorkItemsSourceParameters(updateWorkItemsSourceParametersInput: $updateWorkItemsSourceParametersInput) {
                            success
                            errorMessage
                            updated
                        }
                    } 
            """
            result = client.execute(mutation, variable_values=dict(
                updateWorkItemsSourceParametersInput=dict(
                    connectorKey=str(connector_key),
                    workItemsSourceKeys=[
                        str(work_items_source.key)
                    ],
                    workItemsSourceParameters=dict(
                        initialImportDays=180,
                        syncImportDays=7,
                        parentPathSelectors=[
                            "(fields.issuelinks[?(type.name=='Parent/Child' && outwardIssue.fields.issuetype.name=='Feature')].outwardIssue.key)[0]"
                        ]
                    )
                )))
            assert result.get('errors') is None
            assert result['data']['updateWorkItemsSourceParameters']['success']
            assert result['data']['updateWorkItemsSourceParameters']['updated'] == 1

            with db.orm_session() as session:
                source = WorkItemsSource.find_by_key(session, work_items_source.key)
                assert source.parameters == dict(
                    initial_import_days=180,
                    sync_import_days=7,
                    parent_path_selectors=[
                        "(fields.issuelinks[?(type.name=='Parent/Child' && outwardIssue.fields.issuetype.name=='Feature')].outwardIssue.key)[0]"
                    ]
                )

        def it_only_updates_the_entries_that_are_passed_in(self, setup):
            fixture = setup
            work_items_source = fixture.work_items_source
            connector_key = fixture.connector_key

            with db.orm_session() as session:
                session.add(work_items_source)
                work_items_source.parameters=dict(
                    initial_import_days=180,
                    sync_import_days=7
                )

            client = Client(schema)
            mutation = """
                mutation updateWorkItemsSourceParameters(
                    $updateWorkItemsSourceParametersInput: UpdateWorkItemsSourceParametersInput! 
                    ) {
                        updateWorkItemsSourceParameters(updateWorkItemsSourceParametersInput: $updateWorkItemsSourceParametersInput) {
                            success
                            errorMessage
                            updated
                        }
                    } 
            """
            result = client.execute(mutation, variable_values=dict(
                updateWorkItemsSourceParametersInput=dict(
                    connectorKey=str(connector_key),
                    workItemsSourceKeys=[
                        str(work_items_source.key)
                    ],
                    workItemsSourceParameters=dict(
                        parentPathSelectors=[
                            "(fields.issuelinks[?(type.name=='Parent/Child' && outwardIssue.fields.issuetype.name=='Feature')].outwardIssue.key)[0]"
                        ]
                    )
                )))

            assert result.get('errors') is None
            assert result['data']['updateWorkItemsSourceParameters']['success']
            assert result['data']['updateWorkItemsSourceParameters']['updated'] == 1

            with db.orm_session() as session:
                source = WorkItemsSource.find_by_key(session, work_items_source.key)
                assert source.parameters == dict(
                    initial_import_days=180,
                    sync_import_days=7,
                    parent_path_selectors=[
                        "(fields.issuelinks[?(type.name=='Parent/Child' && outwardIssue.fields.issuetype.name=='Feature')].outwardIssue.key)[0]"
                    ]
                )