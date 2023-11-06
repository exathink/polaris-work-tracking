# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Priya Mukundan

from polaris.common import db
from polaris.work_tracking.db import model
from .fixtures.jira_fixtures import *
from polaris.utils.collections import object_to_dict, Fixture


class TestModel:

    @pytest.fixture()
    def setup(self, jira_work_items_fixture, cleanup):
        work_items, work_items_source, jira_project_id, connector_key = jira_work_items_fixture

        yield Fixture(
            work_items=work_items

        )

    def it_updates_work_item_priority(self, setup):

        fixture = setup

        work_item = [wi for wi in fixture.work_items][0]

        # Check for priority

        work_item_data = dict()
        work_item_data['priority']= 'Medium'
        updated = work_item.update(work_item_data)
        assert updated

    def it_updates_work_item_releases(self, setup):

        fixture = setup

        work_item = [wi for wi in fixture.work_items][0]

        work_item_data = dict()
        work_item_data['releases'] = ["{abc=xyz}"]
        updated = work_item.update(work_item_data)
        assert updated

    def it_updates_work_item_story_points(self, setup):

        fixture = setup

        work_item = [wi for wi in fixture.work_items][0]


        work_item_data = dict()
        work_item_data['story_points'] = 98
        updated = work_item.update(work_item_data)
        assert updated

    def it_updates_work_item_description(self, setup):

        fixture = setup

        work_item = [wi for wi in fixture.work_items][0]

        work_item_data = dict()
        work_item_data['description'] = "New Description"
        updated = work_item.update(work_item_data)
        assert updated

    def it_updates_work_item_name(self, setup):
        fixture = setup

        work_item = [wi for wi in fixture.work_items][0]

        work_item_data = dict()
        work_item_data['name'] = "New Name"
        updated = work_item.update(work_item_data)
        assert updated

    def it_updates_work_item_is_bug(self, setup):
        fixture = setup

        work_item = [wi for wi in fixture.work_items][0]

        work_item_data = dict()
        work_item_data['is_bug'] = not work_item.is_bug
        updated = work_item.update(work_item_data)
        assert updated

    def it_updates_work_item_work_item_type(self, setup):
        fixture = setup

        work_item = [wi for wi in fixture.work_items][0]

        work_item_data = dict()
        work_item_data['work_item_type'] = JiraWorkItemType.bug.value
        updated = work_item.update(work_item_data)
        assert updated

    def it_updates_work_item_is_epic(self, setup):
        fixture = setup

        work_item = [wi for wi in fixture.work_items][0]

        work_item_data = dict()
        work_item_data['is_epic'] = not work_item.is_epic
        updated = work_item.update(work_item_data)
        assert updated

    def it_updates_work_item_tags(self, setup):
        fixture = setup

        work_item = [wi for wi in fixture.work_items][0]

        work_item_data = dict()
        work_item_data['tags'] = ['{new tags}']
        updated = work_item.update(work_item_data)
        assert updated


    def it_updates_work_item_url(self, setup):
        fixture = setup

        work_item = [wi for wi in fixture.work_items][0]

        work_item_data = dict()
        work_item_data['url'] = '/thisisnotaurl'
        updated = work_item.update(work_item_data)
        assert updated

    def it_updates_work_item_source_state(self, setup):
        fixture = setup

        work_item = [wi for wi in fixture.work_items][0]

        work_item_data = dict()
        work_item_data['source_state'] = 'Closed'
        updated = work_item.update(work_item_data)
        assert updated

    def it_updates_work_item_source_display_id(self, setup):
        fixture = setup

        work_item = [wi for wi in fixture.work_items][0]

        work_item_data = dict()
        work_item_data['source_display_id'] = 1005
        updated = work_item.update(work_item_data)
        assert updated

    def it_updates_work_item_parent_id(self, setup):
        fixture = setup

        work_item = [wi for wi in fixture.work_items][0]

        work_item_data = dict()
        work_item_data['parent_id'] = 3
        updated = work_item.update(work_item_data)
        assert updated

    def it_updates_work_item_api_payload(self, setup):
        fixture = setup

        work_item = [wi for wi in fixture.work_items][0]

        work_item_data = dict()
        work_item_data['api_payload'] = '{"id": "10463", "key": "PT-1", "self": "https://exathinkdev.atlassian.net/rest/api/latest/issue/10463", "expand": "operations,versionedRepresentations,editmeta,changelog,customfield_10010.requestTypePractice,renderedFields", "fields": {"votes": {"self": "https://exathinkdev.atlassian.net/rest/api/2/issue/PT-1/votes", "votes": 0, "hasVoted": false}, "labels": [], "status": {"id": "10048", "name": "In Progress", "self": "https://exathinkdev.atlassian.net/rest/api/2/status/10048", "iconUrl": "https://exathinkdev.atlassian.net/", "description": "", "statusCategory": {"id": 4, "key": "indeterminate", "name": "In Progress", "self": "https://exathinkdev.atlassian.net/rest/api/2/statuscategory/4", "colorName": "yellow"}}, "created": "2023-01-09T15:22:25.307-0600", "creator": {"self": "https://exathinkdev.atlassian.net/rest/api/2/user?accountId=629f8ef1c97b1b00687b2091", "active": true, "timeZone": "America/Chicago", "accountId": "629f8ef1c97b1b00687b2091", "avatarUrls": {"16x16": "https://secure.gravatar.com/avatar/d8b346d030eba69e72a6d6865dbf9594?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FPM-3.png", "24x24": "https://secure.gravatar.com/avatar/d8b346d030eba69e72a6d6865dbf9594?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FPM-3.png", "32x32": "https://secure.gravatar.com/avatar/d8b346d030eba69e72a6d6865dbf9594?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FPM-3.png", "48x48": "https://secure.gravatar.com/avatar/d8b346d030eba69e72a6d6865dbf9594?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FPM-3.png"}, "accountType": "atlassian", "displayName": "Priya Mukundan"}, "duedate": null, "project": {"id": "10014", "key": "PT", "name": "Priya-test1", "self": "https://exathinkdev.atlassian.net/rest/api/2/project/10014", "avatarUrls": {"16x16": "https://exathinkdev.atlassian.net/rest/api/2/universal_avatar/view/type/project/avatar/10424?size=xsmall", "24x24": "https://exathinkdev.atlassian.net/rest/api/2/universal_avatar/view/type/project/avatar/10424?size=small", "32x32": "https://exathinkdev.atlassian.net/rest/api/2/universal_avatar/view/type/project/avatar/10424?size=medium", "48x48": "https://exathinkdev.atlassian.net/rest/api/2/universal_avatar/view/type/project/avatar/10424"}, "simplified": true, "projectTypeKey": "software"}, "summary": "Test 11 issue2", "updated": "2023-07-26T13:13:24.682-0500", "watches": {"self": "https://exathinkdev.atlassian.net/rest/api/2/issue/PT-1/watchers", "isWatching": false, "watchCount": 1}, "worklog": {"total": 0, "startAt": 0, "worklogs": [], "maxResults": 20}, "assignee": null, "priority": {"id": "4", "name": "Low", "self": "https://exathinkdev.atlassian.net/rest/api/2/priority/4", "iconUrl": "https://exathinkdev.atlassian.net/images/icons/priorities/low.svg"}, "progress": {"total": 0, "progress": 0}, "reporter": {"self": "https://exathinkdev.atlassian.net/rest/api/2/user?accountId=629f8ef1c97b1b00687b2091", "active": true, "timeZone": "America/Chicago", "accountId": "629f8ef1c97b1b00687b2091", "avatarUrls": {"16x16": "https://secure.gravatar.com/avatar/d8b346d030eba69e72a6d6865dbf9594?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FPM-3.png", "24x24": "https://secure.gravatar.com/avatar/d8b346d030eba69e72a6d6865dbf9594?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FPM-3.png", "32x32": "https://secure.gravatar.com/avatar/d8b346d030eba69e72a6d6865dbf9594?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FPM-3.png", "48x48": "https://secure.gravatar.com/avatar/d8b346d030eba69e72a6d6865dbf9594?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FPM-3.png"}, "accountType": "atlassian", "displayName": "Priya Mukundan"}, "security": null, "subtasks": [], "versions": [], "issuetype": {"id": "10040", "name": "Story", "self": "https://exathinkdev.atlassian.net/rest/api/2/issuetype/10040", "iconUrl": "https://exathinkdev.atlassian.net/rest/api/2/universal_avatar/view/type/issuetype/avatar/10315?size=medium", "subtask": false, "avatarId": 10315, "entityId": "4766b26d-ea9e-4a8b-8a71-7b25d944117b", "description": "Stories track functionality or features expressed as user goals.", "hierarchyLevel": 0}, "timespent": null, "workratio": -1, "attachment": [], "components": [], "issuelinks": [], "lastViewed": null, "resolution": null, "description": null, "environment": null, "fixVersions": [], "timeestimate": null, "timetracking": {}, "resolutiondate": null, "issuerestriction": {"shouldDisplay": true, "issuerestrictions": {}}, "aggregateprogress": {"total": 0, "progress": 0}, "customfield_10000": "{}", "customfield_10001": null, "customfield_10002": null, "customfield_10003": null, "customfield_10004": null, "customfield_10005": null, "customfield_10006": null, "customfield_10007": null, "customfield_10008": null, "customfield_10009": null, "customfield_10010": null, "customfield_10014": null, "customfield_10015": null, "customfield_10016": null, "customfield_10017": null, "customfield_10018": {"showField": false, "nonEditableReason": {"reason": "PLUGIN_LICENSE_ERROR", "message": "The Parent Link is only available to Jira Premium users."}, "hasEpicLinkFieldDependency": false}, "customfield_10019": null, "customfield_10020": null, "customfield_10021": null, "customfield_10022": "0|i002ez:", "customfield_10023": null, "customfield_10024": [], "customfield_10025": null, "customfield_10026": null, "customfield_10030": null, "customfield_10031": null, "customfield_10032": null, "customfield_10033": null, "customfield_10034": null, "customfield_10035": null, "customfield_10036": null, "customfield_10037": [], "customfield_10038": null, "customfield_10039": null, "customfield_10040": null, "customfield_10041": null, "customfield_10042": null, "customfield_10043": null, "customfield_10044": null, "customfield_10045": null, "customfield_10046": null, "customfield_10047": null, "customfield_10048": null, "aggregatetimespent": null, "timeoriginalestimate": null, "aggregatetimeestimate": null, "statuscategorychangedate": "2023-07-26T13:13:10.539-0500", "aggregatetimeoriginalestimate": null}}'
        updated = work_item.update(work_item_data)
        assert updated


    def it_updates_work_item_work_items_source_id(self, setup):
        fixture = setup

        work_item = [wi for wi in fixture.work_items][0]

        work_item_data = dict()
        work_item_data['work_items_source_id'] = 10
        updated = work_item.update(work_item_data)
        assert updated

    def it_updates_work_item_commit_identifiers(self, setup):
        fixture = setup

        work_item = [wi for wi in fixture.work_items][0]

        work_item_data = dict()
        work_item_data['commit_identifiers'] = ["PT-1", "pt-1", "Pt-1"]
        updated = work_item.update(work_item_data)
        assert updated



    def it_updates_work_item_parent_source_display_id(self, setup):
        fixture = setup

        work_item = [wi for wi in fixture.work_items][0]

        work_item_data = dict()
        work_item_data['parent_source_display_id'] = 11
        updated = work_item.update(work_item_data)
        assert updated

    def it_updates_work_item_sprints(self, setup):
        fixture = setup

        work_item = [wi for wi in fixture.work_items][0]

        work_item_data = dict()
        work_item_data['sprints'] = ['Sprint xyz']
        updated = work_item.update(work_item_data)
        assert updated

    def it_updates_work_item_flagged(self, setup):
        fixture = setup

        work_item = [wi for wi in fixture.work_items][0]

        work_item_data = dict()
        work_item_data['flagged'] = True
        updated = work_item.update(work_item_data)
        assert updated