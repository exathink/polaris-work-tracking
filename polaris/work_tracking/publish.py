# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar



from polaris.messaging.utils import publish
from polaris.messaging.topics import WorkItemsTopic
from polaris.messaging.messages import WorkItemsSourceCreated


def work_items_source_created(work_items_source, channel=None):
    message = WorkItemsSourceCreated(
            send=dict(
                organization_key=work_items_source.organization_key,
                work_items_source=dict(
                    name=work_items_source.name,
                    key=work_items_source.key,
                    integration_type=work_items_source.integration_type,
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

