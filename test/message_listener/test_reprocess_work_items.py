#  Copyright (c) Exathink, LCC 2023.
#  All rights reserved
#
# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Priya Mukundan

import json
from unittest.mock import MagicMock

import pkg_resources
from pika.channel import Channel

from polaris.messaging.message_consumer import MessageConsumer
from polaris.messaging.messages import WorkItemsUpdated
from polaris.messaging.test_utils import mock_publisher, mock_channel, assert_topic_and_message, fake_send
from polaris.messaging.topics import WorkItemsTopic
from polaris.utils.token_provider import get_token_provider
from polaris.work_tracking import commands
from polaris.work_tracking.db import api, model
from polaris.work_tracking.integrations.atlassian.jira_work_items_source import JiraProject
from polaris.work_tracking.message_listener import WorkItemsTopicSubscriber
from polaris.work_tracking.messages import ReprocessWorkItems
from polaris.utils.collections import find
from ..fixtures.jira_fixtures import *

jira_api_issue_payload = {'id': '10343', 'self': 'https://urjuna.atlassian.net/rest/api/2/10343', 'key': 'PO-298',
                          'fields': {'statuscategorychangedate': '2020-09-20T13:34:37.712-0500',
                                     'issuetype': {'self': 'https://urjuna.atlassian.net/rest/api/2/issuetype/10103',
                                                   'id': '10103', 'description': 'A problem or error.',
                                                   'iconUrl': 'https://urjuna.atlassian.net/secure/viewavatar?size=medium&avatarId=10303&avatarType=issuetype',
                                                   'name': 'Bug', 'subtask': False, 'avatarId': 10303},
                                     'timespent': None,
                                     'project': {'self': 'https://urjuna.atlassian.net/rest/api/2/project/10008',
                                                 'id': '10008', 'key': 'PO', 'name': 'Polaris',
                                                 'projectTypeKey': 'software', 'simplified': False, 'avatarUrls': {
                                             '48x48': 'https://urjuna.atlassian.net/secure/projectavatar?pid=10008&avatarId=10405',
                                             '24x24': 'https://urjuna.atlassian.net/secure/projectavatar?size=small&s=small&pid=10008&avatarId=10405',
                                             '16x16': 'https://urjuna.atlassian.net/secure/projectavatar?size=xsmall&s=xsmall&pid=10008&avatarId=10405',
                                             '32x32': 'https://urjuna.atlassian.net/secure/projectavatar?size=medium&s=medium&pid=10008&avatarId=10405'}},
                                     'customfield_10110': None, 'fixVersions': [{"id": "10003", "name": "V1", "self": "https://exathinkdev.atlassian.net/rest/api/2/version/10003", "archived": False, "released": False, "description": "", "releaseDate": "2023-08-03"}, {"id": "10004", "name": "V2", "self": "https://exathinkdev.atlassian.net/rest/api/2/version/10004", "archived": False, "released": False, "description": "", "releaseDate": "2023-09-01"}], 'aggregatetimespent': None,
                                     'customfield_10111': None, 'customfield_10112': None, 'resolution': None,
                                     'customfield_10113': None, 'customfield_10114': None, 'customfield_10105': None,
                                     'customfield_10106': [], 'customfield_10107': None, 'customfield_10108': None,
                                     'customfield_10109': None, 'resolutiondate': None, 'workratio': -1,
                                     'issuerestriction': {'issuerestrictions': {}, 'shouldDisplay': False}, 'watches': {
                                  'self': 'https://urjuna.atlassian.net/rest/api/2/issue/PO-298/watchers',
                                  'watchCount': 1, 'isWatching': True}, 'lastViewed': '2020-09-20T18:10:02.551-0500',
                                     'created': '2020-09-20T13:34:25.534-0500', 'customfield_10020': None,
                                     'customfield_10021': None, 'customfield_10100': None,
                                     'priority': {'self': 'https://urjuna.atlassian.net/rest/api/2/priority/3',
                                                  'iconUrl': 'https://urjuna.atlassian.net/images/icons/priorities/medium.svg',
                                                  'name': 'Medium', 'id': '3'}, 'customfield_10101': None,
                                     'labels': ['data-integration', 'incremental-data-management'],
                                     'customfield_10016': 98, 'customfield_10017': None,
                                     'customfield_10018': {'hasEpicLinkFieldDependency': False, 'showField': False,
                                                           'nonEditableReason': {'reason': 'PLUGIN_LICENSE_ERROR',
                                                                                 'message': 'The Parent Link is only available to Jira Premium users.'}},
                                     'customfield_10019': '0|i001vi:', 'timeestimate': None,
                                     'aggregatetimeoriginalestimate': None, 'versions': [], 'issuelinks': [],
                                     'assignee': {
                                         'self': 'https://urjuna.atlassian.net/rest/api/2/user?accountId=5e176e8885a8c90ecaca3c63',
                                         'accountId': '5e176e8885a8c90ecaca3c63', 'avatarUrls': {
                                             '48x48': 'https://secure.gravatar.com/avatar/f4e5904c494e37510101ac9ce50e7ddf?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FPG-2.png',
                                             '24x24': 'https://secure.gravatar.com/avatar/f4e5904c494e37510101ac9ce50e7ddf?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FPG-2.png',
                                             '16x16': 'https://secure.gravatar.com/avatar/f4e5904c494e37510101ac9ce50e7ddf?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FPG-2.png',
                                             '32x32': 'https://secure.gravatar.com/avatar/f4e5904c494e37510101ac9ce50e7ddf?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FPG-2.png'},
                                         'displayName': 'Pragya Goyal', 'active': True, 'timeZone': 'America/Chicago',
                                         'accountType': 'atlassian'}, 'updated': '2020-09-20T18:10:41.502-0500',
                                     'status': {'self': 'https://urjuna.atlassian.net/rest/api/2/status/3',
                                                'description': 'This issue is being actively worked on at the moment by the assignee.',
                                                'iconUrl': 'https://urjuna.atlassian.net/images/icons/statuses/inprogress.png',
                                                'name': 'In Progress', 'id': '3', 'statusCategory': {
                                             'self': 'https://urjuna.atlassian.net/rest/api/2/statuscategory/4',
                                             'id': 4, 'key': 'indeterminate', 'colorName': 'yellow',
                                             'name': 'In Progress'}}, 'components': [], 'timeoriginalestimate': None,
                                     'description': None, 'customfield_10010': None, 'customfield_10014': None,
                                     'customfield_10015': None, 'timetracking': {}, 'customfield_10005': None,
                                     'customfield_10006': None, 'security': None, "customfield_10007": [
                                      {
                                        "id": 4358,
                                        "goal": "",
                                        "name": "Sprint 1",
                                        "state": "active",
                                        "boardId": 293,
                                        "endDate": "2023-08-08T16:09:00.000Z",
                                        "startDate": "2023-07-26T17:11:55.788Z"
                                      }
                                        ],
                                     'customfield_10008': None, 'customfield_10009': None, 'attachment': [],
                                     'aggregatetimeestimate': None, 'summary': 'Jira connector is not mapping labels. ',
                                     'creator': {
                                         'self': 'https://urjuna.atlassian.net/rest/api/2/user?accountId=557058%3Afe3847a4-f489-452f-8a83-0629c51e0455',
                                         'accountId': '557058:fe3847a4-f489-452f-8a83-0629c51e0455', 'avatarUrls': {
                                             '48x48': 'https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png',
                                             '24x24': 'https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png',
                                             '16x16': 'https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png',
                                             '32x32': 'https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png'},
                                         'displayName': 'KrishnaK', 'active': True, 'timeZone': 'America/Chicago',
                                         'accountType': 'atlassian'}, 'subtasks': [], 'reporter': {
                                  'self': 'https://urjuna.atlassian.net/rest/api/2/user?accountId=557058%3Afe3847a4-f489-452f-8a83-0629c51e0455',
                                  'accountId': '557058:fe3847a4-f489-452f-8a83-0629c51e0455', 'avatarUrls': {
                                      '48x48': 'https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png',
                                      '24x24': 'https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png',
                                      '16x16': 'https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png',
                                      '32x32': 'https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png'},
                                  'displayName': 'KrishnaK', 'active': True, 'timeZone': 'America/Chicago',
                                  'accountType': 'atlassian'}, 'customfield_10120': None, 'customfield_10121': None,
                                     'aggregateprogress': {'progress': 0, 'total': 0}, 'customfield_10000': '{}',
                                     'customfield_10122': None, 'customfield_10001': None, 'customfield_10123': None,
                                     'customfield_10002': None, 'customfield_10003': None, 'customfield_10124': None,
                                     'customfield_10125': None, 'customfield_10004': None, 'customfield_10115': None,
                                     'customfield_10116': None, 'customfield_10117': None, 'environment': None,
                                     'customfield_10118': None, 'customfield_10119': None, 'duedate': None,
                                     'progress': {'progress': 0, 'total': 0},
                                     'votes': {'self': 'https://urjuna.atlassian.net/rest/api/2/issue/PO-298/votes',
                                               'votes': 0, 'hasVoted': False}}}

jira_api_issue_payload_updated = {'id': '10343', 'self': 'https://urjuna.atlassian.net/rest/api/2/10343', 'key': 'PO-298',
                          'fields': {'statuscategorychangedate': '2020-09-20T13:34:37.712-0500',
                                     'issuetype': {'self': 'https://urjuna.atlassian.net/rest/api/2/issuetype/10103',
                                                   'id': '10103', 'description': 'A problem or error.',
                                                   'iconUrl': 'https://urjuna.atlassian.net/secure/viewavatar?size=medium&avatarId=10303&avatarType=issuetype',
                                                   'name': 'Bug', 'subtask': False, 'avatarId': 10303},
                                     'timespent': None,
                                     'project': {'self': 'https://urjuna.atlassian.net/rest/api/2/project/10008',
                                                 'id': '10008', 'key': 'PO', 'name': 'Polaris',
                                                 'projectTypeKey': 'software', 'simplified': False, 'avatarUrls': {
                                             '48x48': 'https://urjuna.atlassian.net/secure/projectavatar?pid=10008&avatarId=10405',
                                             '24x24': 'https://urjuna.atlassian.net/secure/projectavatar?size=small&s=small&pid=10008&avatarId=10405',
                                             '16x16': 'https://urjuna.atlassian.net/secure/projectavatar?size=xsmall&s=xsmall&pid=10008&avatarId=10405',
                                             '32x32': 'https://urjuna.atlassian.net/secure/projectavatar?size=medium&s=medium&pid=10008&avatarId=10405'}},
                                     'customfield_10110': None, 'fixVersions': [{"id": "10003", "name": "V1", "self": "https://exathinkdev.atlassian.net/rest/api/2/version/10003", "archived": False, "released": False, "description": "", "releaseDate": "2023-08-03"}, {"id": "10004", "name": "V2", "self": "https://exathinkdev.atlassian.net/rest/api/2/version/10004", "archived": False, "released": False, "description": "", "releaseDate": "2023-09-01"}], 'aggregatetimespent': None,
                                     'customfield_10111': None, 'customfield_10112': None, 'resolution': None,
                                     'customfield_10113': None, 'customfield_10114': None, 'customfield_10105': None,
                                     'customfield_10106': [], 'customfield_10107': None, 'customfield_10108': None,
                                     'customfield_10109': None, 'resolutiondate': None, 'workratio': -1,
                                     'issuerestriction': {'issuerestrictions': {}, 'shouldDisplay': False}, 'watches': {
                                  'self': 'https://urjuna.atlassian.net/rest/api/2/issue/PO-298/watchers',
                                  'watchCount': 1, 'isWatching': True}, 'lastViewed': '2020-09-20T18:10:02.551-0500',
                                     'created': '2020-09-20T13:34:25.534-0500', 'customfield_10020': None,
                                     'customfield_10021': None, 'customfield_10100': None,
                                     'priority': {'self': 'https://urjuna.atlassian.net/rest/api/2/priority/3',
                                                  'iconUrl': 'https://urjuna.atlassian.net/images/icons/priorities/low.svg',
                                                  'name': 'Low', 'id': '3'}, 'customfield_10101': None,
                                     'labels': ['data-integration', 'incremental-data-management'],
                                     'customfield_10016': 98, 'customfield_10017': None,
                                     'customfield_10018': {'hasEpicLinkFieldDependency': False, 'showField': False,
                                                           'nonEditableReason': {'reason': 'PLUGIN_LICENSE_ERROR',
                                                                                 'message': 'The Parent Link is only available to Jira Premium users.'}},
                                     'customfield_10019': '0|i001vi:', 'timeestimate': None,
                                     'aggregatetimeoriginalestimate': None, 'versions': [], 'issuelinks': [],
                                     'assignee': {
                                         'self': 'https://urjuna.atlassian.net/rest/api/2/user?accountId=5e176e8885a8c90ecaca3c63',
                                         'accountId': '5e176e8885a8c90ecaca3c63', 'avatarUrls': {
                                             '48x48': 'https://secure.gravatar.com/avatar/f4e5904c494e37510101ac9ce50e7ddf?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FPG-2.png',
                                             '24x24': 'https://secure.gravatar.com/avatar/f4e5904c494e37510101ac9ce50e7ddf?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FPG-2.png',
                                             '16x16': 'https://secure.gravatar.com/avatar/f4e5904c494e37510101ac9ce50e7ddf?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FPG-2.png',
                                             '32x32': 'https://secure.gravatar.com/avatar/f4e5904c494e37510101ac9ce50e7ddf?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FPG-2.png'},
                                         'displayName': 'Pragya Goyal', 'active': True, 'timeZone': 'America/Chicago',
                                         'accountType': 'atlassian'}, 'updated': '2020-09-20T18:10:41.502-0500',
                                     'status': {'self': 'https://urjuna.atlassian.net/rest/api/2/status/3',
                                                'description': 'This issue is being actively worked on at the moment by the assignee.',
                                                'iconUrl': 'https://urjuna.atlassian.net/images/icons/statuses/inprogress.png',
                                                'name': 'In Progress', 'id': '3', 'statusCategory': {
                                             'self': 'https://urjuna.atlassian.net/rest/api/2/statuscategory/4',
                                             'id': 4, 'key': 'indeterminate', 'colorName': 'yellow',
                                             'name': 'In Progress'}}, 'components': [], 'timeoriginalestimate': None,
                                     'description': None, 'customfield_10010': None, 'customfield_10014': None,
                                     'customfield_10015': None, 'timetracking': {}, 'customfield_10005': None,
                                     'customfield_10006': None, 'security': None, "customfield_10007": [
                                      {
                                        "id": 4358,
                                        "goal": "",
                                        "name": "Sprint 1",
                                        "state": "active",
                                        "boardId": 293,
                                        "endDate": "2023-08-08T16:09:00.000Z",
                                        "startDate": "2023-07-26T17:11:55.788Z"
                                      }
                                        ],
                                     'customfield_10008': None, 'customfield_10009': None, 'attachment': [],
                                     'aggregatetimeestimate': None, 'summary': 'Jira connector is not mapping labels. ',
                                     'creator': {
                                         'self': 'https://urjuna.atlassian.net/rest/api/2/user?accountId=557058%3Afe3847a4-f489-452f-8a83-0629c51e0455',
                                         'accountId': '557058:fe3847a4-f489-452f-8a83-0629c51e0455', 'avatarUrls': {
                                             '48x48': 'https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png',
                                             '24x24': 'https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png',
                                             '16x16': 'https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png',
                                             '32x32': 'https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png'},
                                         'displayName': 'KrishnaK', 'active': True, 'timeZone': 'America/Chicago',
                                         'accountType': 'atlassian'}, 'subtasks': [], 'reporter': {
                                  'self': 'https://urjuna.atlassian.net/rest/api/2/user?accountId=557058%3Afe3847a4-f489-452f-8a83-0629c51e0455',
                                  'accountId': '557058:fe3847a4-f489-452f-8a83-0629c51e0455', 'avatarUrls': {
                                      '48x48': 'https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png',
                                      '24x24': 'https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png',
                                      '16x16': 'https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png',
                                      '32x32': 'https://secure.gravatar.com/avatar/ff19230d4b6d9a5d7d441dc62fec4619?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FK-2.png'},
                                  'displayName': 'KrishnaK', 'active': True, 'timeZone': 'America/Chicago',
                                  'accountType': 'atlassian'}, 'customfield_10120': None, 'customfield_10121': None,
                                     'aggregateprogress': {'progress': 0, 'total': 0}, 'customfield_10000': '{}',
                                     'customfield_10122': None, 'customfield_10001': None, 'customfield_10123': None,
                                     'customfield_10002': None, 'customfield_10003': None, 'customfield_10124': None,
                                     'customfield_10125': None, 'customfield_10004': None, 'customfield_10115': None,
                                     'customfield_10116': None, 'customfield_10117': None, 'environment': None,
                                     'customfield_10118': None, 'customfield_10119': None, 'duedate': None,
                                     'progress': {'progress': 0, 'total': 0},
                                     'votes': {'self': 'https://urjuna.atlassian.net/rest/api/2/issue/PO-298/votes',
                                               'votes': 0, 'hasVoted': False}}}





mock_channel = MagicMock(Channel)
mock_consumer = MagicMock(MessageConsumer)
mock_consumer.token_provider = get_token_provider()


class TestReprocessWorkItems(WorkItemsSourceTest):

    class TestMessagePublishing:
        @pytest.fixture
        def setup(self, setup, cleanup):

           fixture = setup
           work_items_source = fixture.work_items_source


           with db.orm_session() as session:
               session.add(work_items_source)
               project = JiraProject(work_items_source)

           yield Fixture(
               organization_key=organization_key,
               project=project,
               work_items_source=work_items_source,
               connector_key=work_items_source.connector_key,
               original_issue=jira_api_issue_payload,
               updated_issue = jira_api_issue_payload
           )



        def it_publishes_work_items_updated_messages_when_there_are_changes(self,setup):

            fixture = setup
            project=fixture.project
            organization_key = fixture.organization_key
            work_items_source = fixture.work_items_source
            mapped_data = project.map_issue_to_work_item_data(jira_api_issue_payload)
            initial_state = api.sync_work_items(work_items_source.key, [mapped_data])

            mapped_data = project.map_issue_to_work_item_data(jira_api_issue_payload_updated)
            mapped_data['priority'] = 'Medium'

            with db.orm_session() as session:
                session.add(work_items_source)
                work_item = work_items_source.work_items[0]
                work_item.update(mapped_data)

            message = fake_send(
                ReprocessWorkItems(send=dict(
                    organization_key=organization_key,
                    work_items_source_key=work_items_source.key,
                    attributes_to_check=['priority']
                ))
            )
            publisher = mock_publisher()
            subscriber = WorkItemsTopicSubscriber(mock_channel, publisher=publisher)
            subscriber.consumer_context = mock_consumer

            messages = subscriber.dispatch(mock_channel, message)
            assert len(messages) == 1

            publisher.assert_topic_called_with_message(WorkItemsTopic, WorkItemsUpdated, call_count=1)


        def it_does_not_publish_work_items_updated_messages_when_there_are_no_changes(self,setup):

            fixture = setup
            project=fixture.project
            organization_key = fixture.organization_key
            work_items_source = fixture.work_items_source
            mapped_data = project.map_issue_to_work_item_data(jira_api_issue_payload)
            initial_state = api.sync_work_items(work_items_source.key, [mapped_data])

            message = fake_send(
                ReprocessWorkItems(send=dict(
                    organization_key=organization_key,
                    work_items_source_key=work_items_source.key,
                    attributes_to_check=['priority']
                ))
            )
            publisher = mock_publisher()
            subscriber = WorkItemsTopicSubscriber(mock_channel, publisher=publisher)
            subscriber.consumer_context = mock_consumer

            messages = subscriber.dispatch(mock_channel, message)
            assert len(messages) == 0

            publisher.assert_not_called()


