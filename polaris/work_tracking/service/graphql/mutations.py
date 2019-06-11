# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging

import graphene

from polaris.common.enums import WorkTrackingIntegrationType
from polaris.work_tracking import work_tracker
from polaris.work_tracking.integrations import pivotal_tracker, github
from polaris.work_tracking.integrations.atlassian import jira_work_items_source

logger = logging.getLogger('polaris.work_tracking.mutations')


# Input Types
IntegrationType = graphene.Enum.from_enum(WorkTrackingIntegrationType)
GithubSourceType = graphene.Enum.from_enum(github.GithubWorkItemSourceType)
PivotalSourceType = graphene.Enum.from_enum(pivotal_tracker.PivotalWorkItemSourceType)
JiraSourceType = graphene.Enum.from_enum(jira_work_items_source.JiraWorkItemSourceType)

class CommitMappingScope(graphene.Enum):
    organization = 'organization'
    project = 'project'
    repository = 'repository'


class GithubWorkItemSourceParams(graphene.InputObjectType):
    work_items_source_type = GithubSourceType(required=True)

    organization = graphene.String(required=True)
    repository = graphene.String(required=False)
    bug_tags = graphene.List(graphene.String)


class PivotalWorkItemsSourceParams(graphene.InputObjectType):
    work_items_source_type = PivotalSourceType(required=True)

    name = graphene.String(required=True)
    id = graphene.String(required=True)


class JiraWorkItemsSourceParams(graphene.InputObjectType):
    work_items_source_type = JiraSourceType(required=True)
    jira_connector_key = graphene.String(required=True)
    project_id = graphene.String(required=True)
    initial_import_days = graphene.Int(required=False)



class WorkItemsSourceInput(graphene.InputObjectType):
    key = graphene.String(required=False)
    integration_type = IntegrationType(required=True)
    name = graphene.String(required=True)
    pivotal_parameters = PivotalWorkItemsSourceParams(required=False)
    github_parameters = GithubWorkItemSourceParams(required=False)
    jira_parameters = JiraWorkItemsSourceParams(required=False)

    description = graphene.String(required=False)
    account_key = graphene.String(required=True)
    organization_key = graphene.String(required=True)
    commit_mapping_scope = CommitMappingScope(required=True)
    commit_mapping_scope_key = graphene.String(required=True)


# Mutations

class CreateWorkItemsSource(graphene.Mutation):
    class Arguments:
        data = WorkItemsSourceInput(required=True)

    name = graphene.String()
    key = graphene.String()

    def mutate(self, info, data):
        logger.info('CreateWorkItemsSource called')
        work_items_source = work_tracker.create_work_items_source(work_items_source_input=data)
        return CreateWorkItemsSource(
            name=work_items_source.name,
            key=work_items_source.key
        )


