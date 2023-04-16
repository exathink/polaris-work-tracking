# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2019) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import graphene


class WorkItemsSourceInfo(graphene.Interface):
    description = graphene.String()
    url = graphene.String()
    account_key = graphene.String()
    organization_key = graphene.String()
    integration_type = graphene.String()
    import_state = graphene.String()
    initial_import_days = graphene.Int()


class WorkItemsSourceParameters(graphene.InputObjectType):
    initial_import_days=graphene.Int(required=False, description="Days of data to import on initial import")
    sync_import_days=graphene.Int(required=False, description="Days of data to import on subsequent sync operations")
    parent_path_selectors=graphene.List(graphene.String, required=False,
                                        description="""
                                        Array of jmespath expressions to select a parent key 
                                        from the json api payload for a work item fetched from this source.
                                        The expressions are evaluated in sequence and the value returned by the first
                                        non-null selector is used as the the parent key. The key here should be a user facing key
                                        and not the internal source identifier. 
                                        """)


class WorkItemCount(graphene.Interface):
    work_item_count = graphene.Int()
