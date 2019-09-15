# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar


from polaris.messaging.messages import WorkItemsSourceCreated, ProjectImported
from polaris.messaging.topics import WorkItemsTopic, ConnectorsTopic
from polaris.messaging.utils import publish
from polaris.work_tracking.messages import AtlassianConnectWorkItemEvent, RefreshConnectorProjects


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
