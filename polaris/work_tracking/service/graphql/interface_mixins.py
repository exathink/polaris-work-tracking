# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2019) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from polaris.graphql.mixins import KeyIdResolverMixin
from polaris.graphql.utils import create_tuple, init_tuple

from .interfaces import WorkItemsSourceInfo, WorkItemCount


class WorkItemsSourceInfoResolverMixin(KeyIdResolverMixin):
    work_items_source_info_tuple = create_tuple(WorkItemsSourceInfo)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.work_items_source_info = init_tuple(self.work_items_source_info_tuple, **kwargs)

    def resolve_work_items_source_info(self, info, **kwargs):
        return self.resolve_interface_for_instance(
            interface=['WorkItemsSourceInfo'],
            params=self.get_instance_query_params(),
            **kwargs
        )

    def get_work_items_source_info(self, info, **kwargs):
        if self.work_items_source_info is None:
            self.work_items_source_info = self.resolve_work_items_source_info(info, **kwargs)
        return self.work_items_source_info

    def resolve_url(self, info, **kwargs):
        return self.get_work_items_source_info(info, **kwargs).url

    def resolve_description(self, info, **kwargs):
        return self.get_work_items_source_info(info, **kwargs).description

    def resolve_account_key(self, info, **kwargs):
        return self.get_work_items_source_info(info, **kwargs).account_key

    def resolve_organization_key(self, info, **kwargs):
        return self.get_work_items_source_info(info, **kwargs).organization_key

    def resolve_integration_type(self, info, **kwargs):
        return self.get_work_items_source_info(info, **kwargs).integration_type


class WorkItemCountResolverMixin(KeyIdResolverMixin):
    work_item_count_tuple = create_tuple(WorkItemsSourceInfo)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.work_item_count = init_tuple(self.work_item_count_tuple, **kwargs)

    def resolve_work_item_count(self, info, **kwargs):
        return self.resolve_interface_for_instance(
            interface=['WorkItemCount'],
            params=self.get_instance_query_params(),
            **kwargs
        )

    def get_work_item_count(self, info, **kwargs):
        if self.work_item_count is None:
            self.work_item_count = self.resolve_work_item_count(info, **kwargs)
        return self.work_item_count

    def resolve_work_item_count(self, info, **kwargs):
        return self.get_work_item_count(info, **kwargs).work_item_count