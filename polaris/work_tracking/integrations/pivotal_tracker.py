# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import requests
import logging
from polaris.work_tracking.db.model import WorkItemSourceType

logger = logging.getLogger('polaris.work_tracking.pivotal_tracker')


class PivotalTrackerWorkItemsSource:



    @staticmethod
    def create(token_provider, work_items_source):
        assert work_items_source.integration_type == WorkItemSourceType.pivotal.value

        if work_items_source.work_items_source_type == 'project':
            return PivotalTrackerProject(token_provider, work_items_source)


class PivotalTrackerProject(PivotalTrackerWorkItemsSource):

    def __init__(self, token_provider, work_items_source):
        self.access_token = token_provider.get_token(work_items_source.account_key, work_items_source.organization_key,
                                                     'pivotal_tracker_api_key')
        self.work_items_source = work_items_source
        self.project_id = work_items_source.parameters.get('id')
        self.base_url = 'https://www.pivotaltracker.com/services/v5'
        self.last_updated = work_items_source.latest_work_item_update_timestamp

    def fetch_work_items_to_sync(self):
        if self.work_items_source.should_sync():
            query_params = dict(limit=100)
            if self.last_updated:
                query_params['updated_after'] = self.last_updated.isoformat()

            response = requests.get(
                f'{self.base_url}/projects/{self.project_id}/stories',
                headers={"X-TrackerToken": self.access_token},
                params=query_params
            )
            if response.ok:
                offset = 0
                total = int(response.headers.get('X-Tracker-Pagination-Total'))
                while offset < total and response.ok:
                    stories = response.json()
                    if len(stories) == 0:
                        break

                    work_items = [
                        dict(
                            name=story.get('name'),
                            description=story.get('description'),
                            is_bug=story.get('story_type') == 'bug',
                            tags=[story.get('story_type')] + [label.get('name') for label in story.get('labels')],
                            url=story.get('url'),
                            source_id=str(story.get('id')),
                            source_last_updated=story.get('updated_at'),
                            source_created_at=story.get('created_at'),
                            source_display_id=story.get('id'),
                            source_state=story.get('current_state')

                        )
                        for story in stories
                    ]
                    yield work_items

                    offset = offset + len(work_items)
                    query_params['offset'] = offset
                    response = requests.get(
                        f'{self.base_url}/projects/{self.project_id}/stories',
                        headers={"X-TrackerToken": self.access_token},
                        params=query_params
                    )
                    total = int(response.headers.get('X-Tracker-Pagination-Total'))

        else:
            logger.info(f'Work Item source does not need to be synced. Last synced: '
                        f'{self.work_items_source.last_synced}')
