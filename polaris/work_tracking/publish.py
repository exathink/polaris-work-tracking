# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar


from polaris.messaging.messages import WorkItemsSourceCreated, ProjectImported, \
    WorkItemsCreated, WorkItemsUpdated
from polaris.messaging.topics import WorkItemsTopic, ConnectorsTopic
from polaris.messaging.utils import publish
from polaris.work_tracking.messages import AtlassianConnectWorkItemEvent, RefreshConnectorProjects, \
    ResolveWorkItemsForEpic, GitlabProjectEvent

from polaris.integrations.publish import connector_event

def work_items_source_created(work_items_source, channel=None):
    message = WorkItemsSourceCreated(
        send=dict(
            organization_key=work_items_source.organization_key,
            work_items_source=dict(
                name=work_items_source.name,
                key=work_items_source.key,
                integration_type=work_items_source.integration_type,
                work_items_source_type=work_items_source.work_items_source_type,
                commit_mapping_scope=work_items_source.commit_mapping_scope,
                commit_mapping_scope_key=work_items_source.commit_mapping_scope_key
            )
        )
    )
    publish(
        WorkItemsTopic,
        message,
        channel=channel
    )
    return message


def atlassian_connect_work_item_event(atlassian_connector_key, atlassian_event_type, atlassian_event, channel=None):
    message = AtlassianConnectWorkItemEvent(
        send=dict(
            atlassian_connector_key=atlassian_connector_key,
            atlassian_event_type=atlassian_event_type,
            atlassian_event=atlassian_event
        )
    )
    publish(
        WorkItemsTopic,
        message,
        channel=channel
    )
    return message


def project_imported(organization_key, project, channel=None):
    message = ProjectImported(
        send=dict(
            organization_key=organization_key,
            project_summary=dict(
                key=project.key,
                name=project.name,
                organization_key=project.organization_key,
                work_items_sources=[
                    dict(
                        key=work_items_source.key,
                        name=work_items_source.name,
                        description=work_items_source.description,
                        integration_type=work_items_source.integration_type,
                        work_items_source_type=work_items_source.work_items_source_type,
                        commit_mapping_scope=work_items_source.commit_mapping_scope,
                        commit_mapping_scope_key=work_items_source.commit_mapping_scope_key,
                        source_id=work_items_source.source_id
                    )
                    for work_items_source in project.work_items_sources
                ]
            )
        )
    )
    publish(
        WorkItemsTopic,
        message,
        channel=channel
    )
    return message


def refresh_connector_projects(connector_key, tracking_receipt=None, channel=None):
    message = RefreshConnectorProjects(
        send=dict(
            connector_key=connector_key,
            tracking_receipt_key=tracking_receipt.key if tracking_receipt else None
        )
    )
    publish(
        ConnectorsTopic,
        message,
        channel=channel
    )
    return message


def resolve_work_items_for_epic(organization_key, work_items_source_key, epic, channel=None):
    message = ResolveWorkItemsForEpic(
        send=dict(
            organization_key=organization_key,
            work_items_source_key=work_items_source_key,
            epic=epic
        )
    )
    publish(
        WorkItemsTopic,
        message,
        channel=channel
    )
    return message


def gitlab_project_event(event_type, connector_key, payload, channel=None):
    message = GitlabProjectEvent(
        send=dict(
            event_type=event_type,
            connector_key=connector_key,
            payload=payload
        )
    )
    publish(
        WorkItemsTopic,
        message,
        channel=channel
    )
    return message


def work_item_created_event(organization_key, work_items_source_key, new_work_items, channel=None):
    message = WorkItemsCreated(
        send=dict(
            organization_key=organization_key,
            work_items_source_key=work_items_source_key,
            new_work_items=new_work_items
        )
    )
    publish(
        WorkItemsTopic,
        message,
        channel=channel
    )


def work_item_updated_event(organization_key, work_items_source_key, updated_work_items, channel=None):
    message = WorkItemsCreated(
        send=dict(
            organization_key=organization_key,
            work_items_source_key=work_items_source_key,
            update_work_items=updated_work_items
        )
    )
    publish(
        WorkItemsTopic,
        message,
        channel=channel
    )


# This shim is here only to explictly mark connector event as a referenced symbol.
# PyCharm apparently does not correctly recognize re-exported names. In this case publish.connector_events
# is marked as an unreferenced name and optimized out if we do optimize imports. This causes run time failures
# when this function is called. Hacky fix is to simply assign this imported name to _dont_optimize_import
# so the import is
# not optimized out by mistake.
_dont_optimize_import = (connector_event,)
