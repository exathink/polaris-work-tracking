# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2020) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from polaris.utils.collections import Fixture
from .fixtures.jira_fixtures import *
from polaris.work_tracking.integrations.atlassian.jira_work_items_source import JiraProject
from polaris.common import db

# Serialized version of a jira message for issue. Use as mock for unit tests that work with issue objects.
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
                                     'customfield_10110': None, 'fixVersions': [], 'aggregatetimespent': None,
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
                                     'customfield_10016': None, 'customfield_10017': None,
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
                                     'customfield_10006': None, 'security': None, 'customfield_10007': None,
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


class TestJiraWorkItemSource:

    @pytest.yield_fixture
    def setup(self, jira_work_item_source_fixture):
        work_items_source, _, _ = jira_work_item_source_fixture

        with db.orm_session() as session:
            session.add(work_items_source)
            jira_project = JiraProject(work_items_source)

        yield Fixture(
            jira_project=jira_project,
            jira_issue=jira_api_issue_payload
        )

    def it_maps_work_item_data_correctly(self, setup):
        fixture = setup

        project = fixture.jira_project

        mapped_data = project.map_issue_to_work_item_data(fixture.jira_issue)

        assert mapped_data

        assert mapped_data['name']
        assert not mapped_data['description']
        assert mapped_data['is_bug']
        assert mapped_data['work_item_type'] == 'bug'
        assert len(mapped_data['tags']) == 2
        assert mapped_data['url']
        assert mapped_data['source_id']
        assert mapped_data['source_display_id']
        assert mapped_data['source_last_updated']
        assert mapped_data['source_created_at']
        assert mapped_data['source_state']
        assert not mapped_data['is_epic']
        assert not mapped_data['epic_source_display_id']
        # explicitly assert that these are the only fields mapped. The test should fail
        # and force a change in assertions if we change the mapping
        assert len(mapped_data.keys()) == 13