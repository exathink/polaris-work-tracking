# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar
__version__ = '0.0.1'

import graphene

from polaris.graphql.interfaces import NamedNode


class Query(graphene.ObjectType):
    node = NamedNode.Field()
    ping = graphene.String()

    def resolve_ping(self, info, **kwargs):
        return 'pong'

schema = graphene.Schema(query=Query)
