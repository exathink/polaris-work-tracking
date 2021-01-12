# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Pragya Goyal

import json

from polaris.vcs.messaging import publish
from polaris.common import db
from polaris.repos.db.model import Repository
from polaris.work_tracking import connector_factory
from polaris.work_tracking.db import api
from polaris.work_tracking.integrations.gitlab import GitlabProject


def handle_issue_event():
    pass


def handle_project_event():
    pass


def handle_gitlab_event(connector_key, event_type, payload, channel=None):
    if event_type == 'issue':
        return handle_issue_event(connector_key, payload, channel)
    if event_type == 'push':
        return handle_project_event(connector_key, payload, channel)

