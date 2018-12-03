# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging

from polaris.utils.logging import config_logging
from polaris.utils.config import get_config_provider
from polaris.messaging.messages import \
    CommitsCreated, \
    CommitsWorkItemsResolved, \
    WorkItemsCommitsResolved, \
    WorkItemsCommitsUpdated

from polaris.messaging.topics import CommitsTopic, WorkItemsTopic, TopicSubscriber
from polaris.messaging.message_consumer import MessageConsumer

from polaris.work_tracking import work_tracker
from polaris.common import db


logger = logging.getLogger('polaris.work_tracking.message_listener')


class CommitsTopicSubscriber(TopicSubscriber):
    def __init__(self, channel):
        super().__init__(
            topic = CommitsTopic(channel, create=True),
            subscriber_queue='commits_work_items',
            message_classes=[
                CommitsCreated
            ],
            exclusive=False,
            no_ack=True
        )


    def dispatch(self, channel, message):
        if CommitsCreated.message_type == message.message_type:
            resolved = self.process_commits_created(message)
            if resolved:
               commit_work_items_resolved_message = CommitsWorkItemsResolved(send=resolved[0], in_response_to=message)
               CommitsTopic(channel).publish(message=commit_work_items_resolved_message)

               work_items_commits_resolved_message = WorkItemsCommitsResolved(send=resolved[1], in_response_to=message)
               WorkItemsTopic(channel).publish(message=work_items_commits_resolved_message)
               return commit_work_items_resolved_message, work_items_commits_resolved_message


    @staticmethod
    def process_commits_created(message):
        commits_created=message.dict
        organization_key = commits_created['organization_key']
        repository_name = commits_created['repository_name']
        logger.info(f"Processing  {message.message_type}: "
                    f" Organization: {organization_key}"
                    f" Repository: {repository_name}")

        resolved_work_items = work_tracker.resolve_work_items_from_commit_headers(
            organization_key,
            commits_created['new_commits']
        )
        if resolved_work_items is not None:
            logger.info(f'Resolved new work_items for {len(resolved_work_items[0])} commits for organization {organization_key} and repository {repository_name}')
            return dict(
               organization_key=organization_key,
               repository_name=repository_name,
               commits_work_items=resolved_work_items[0]
           ), dict(
                organization_key=organization_key,
                repository_name=repository_name,
                work_items_commits=resolved_work_items[1]
            )


#-------------------------------------------------
#
# ------------------------------------------------

class WorkItemsTopicSubscriber(TopicSubscriber):
    def __init__(self, channel):
        super().__init__(
            topic = WorkItemsTopic(channel, create=True),
            subscriber_queue='work_items_work_items',
            message_classes=[
                WorkItemsCommitsResolved
            ],
            exclusive=False,
            no_ack=True
        )

    def dispatch(self, channel, message ):
        if WorkItemsCommitsResolved.message_type == message.message_type:
            result = self.process_work_items_commits_resolved(message)
            if result:
                work_items_commits_updated_message = WorkItemsCommitsUpdated(
                    send=result,
                    in_response_to=message
                )
                WorkItemsTopic(channel).publish(message=work_items_commits_updated_message)
                return work_items_commits_updated_message

    @staticmethod
    def process_work_items_commits_resolved(message):
        work_items_commits_resolved = message.dict
        organization_key = work_items_commits_resolved['organization_key']
        repository_name = work_items_commits_resolved['repository_name']
        logger.info(f"Processing  {message.message_type}: "
                    f" Organization: {organization_key}"
                    f" Repository: {repository_name}")

        work_tracker.update_work_items_commits(organization_key, repository_name, work_items_commits_resolved['work_items_commits'])
        return work_items_commits_resolved



if __name__ == "__main__":
    config_logging()
    config_provider = get_config_provider()

    logger.info('Connecting to polaris db...')
    db.init(config_provider.get('POLARIS_DB_URL'))

    MessageConsumer(
        name='polaris.work_tracking.message_listener',
        topic_subscriber_classes=[
            CommitsTopicSubscriber,
            WorkItemsTopicSubscriber
        ]
    ).start_consuming()






