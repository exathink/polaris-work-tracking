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








class WorkItemCount(graphene.Interface):
    work_item_count = graphene.Int()
