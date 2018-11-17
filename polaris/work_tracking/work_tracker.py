# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar



from polaris.work_tracking.db import api

from polaris.work_tracking.work_items_source_factory import create_work_items_source

def sync_work_items(token_provider, work_items_source_key):
    work_items_source = create_work_items_source(token_provider, work_items_source_key)

    import_count = 0
    for work_items in work_items_source.fetch_work_items_to_sync():
        api.sync_work_items(work_items_source_key, work_items)
        import_count = import_count + len(work_items)

    return import_count

