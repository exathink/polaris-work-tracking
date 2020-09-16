# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal

import pytest
from unittest.mock import patch
from test.fixtures.jira_fixtures import *


class TestImportProjectCustomFields:

    @pytest.yield_fixture
    def setup(self, jira_work_item_source_fixture):
        pass

    class TestJiraProjectCustomFieldsImport:

        def setup(self):
            pass

        class WhenWorkItemsSourceExists:

            def it_imports_custom_fields(self):
                with patch(
                        'polaris.work_tracking.integrations.atlassian.jira_connector.JiraConnector.fetch_custom_fields') as fetch_custom_fields:
                    fetch_custom_fields.return_value = [[dict(name='Epic Link', id='customfield_10014', key='customfield_10014')]]


        class WhenWorkItemsSourceDoesNotExist:

            def it_does_not_import_but_returns_message_work_items_source_not_available_for_this_import(self):
                pass

        class WhenInputKeyDoesNotMatchUUIDFormat:

            def it_returns_failure_message(self):
                pass

    class TestPivotalCustomFieldsImport:

        def setup(self):
            pass

        class WhenWorkItemsSourceExists:

            def it_does_not_import_but_returns_message_work_items_source_not_available_for_this_import(self):
                pass

        class WhenWorkItemsSourceDoesNotExist:

            def it_returns_error_message(self):
                pass

    class TestGithubCustomFieldsImport:

        def setup(self):
            pass

        class WhenWorkItemsSourceExists:

            def it_does_not_import_but_returns_message_work_items_source_not_available_for_this_import(self):
                pass

        class WhenWorkItemsSourceDoesNotExist:

            def it_returns_error_message(self):
                pass
