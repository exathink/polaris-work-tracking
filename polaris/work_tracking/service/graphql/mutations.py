# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging
import graphene

from polaris.work_tracking.db.model import WorkItemSourceType
from polaris.work_tracking import work_tracker

logger = logging.getLogger('polaris.work_tracking.mutations')


# Input Types
IntegrationType = graphene.Enum.from_enum(WorkItemSourceType)


class CommitMappingScope(graphene.Enum):
    organization = 'organization'
    project = 'project'
    repository = 'repository'


class GithubWorkItemSourceParams(graphene.InputObjectType):
    organization = graphene.String(required=True)
    repository = graphene.String(required=False)
    bug_tags = graphene.List(graphene.String)


class PivotalWorkItemsSourceParams(graphene.InputObjectType):
    name = graphene.String(required=True)
    id = graphene.String(required=True)


class WorkItemsSourceInput(graphene.InputObjectType):
    key = graphene.String(required=False)
    integration_type = IntegrationType(required=True)
    name = graphene.String(required=True)
    work_items_source_type = graphene.String(required=True)
    pivotal_parameters = PivotalWorkItemsSourceParams(required=False)
    github_parameters = GithubWorkItemSourceParams(required=False)
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
