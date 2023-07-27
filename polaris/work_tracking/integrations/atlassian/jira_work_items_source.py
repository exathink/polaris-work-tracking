# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import logging
from datetime import datetime, timedelta
import jmespath

from polaris.utils.collections import find

import polaris.work_tracking.connector_factory
from polaris.common.enums import JiraWorkItemType, JiraWorkItemSourceType
from polaris.utils.exceptions import ProcessingException
from polaris.work_tracking.enums import CustomTagMappingType

logger = logging.getLogger('polaris.work_tracking.jira')


class JiraWorkItemsSource:

    @staticmethod
    def create(token_provider, work_items_source):
        if work_items_source.work_items_source_type == JiraWorkItemSourceType.project.value:
            return JiraProject(work_items_source)
        else:
            raise ProcessingException(f"Unknown work items source type {work_items_source.work_items_source_type}")


class JiraProject(JiraWorkItemsSource):

    def __init__(self, work_items_source):

        self.work_items_source = work_items_source
        self.project_id = work_items_source.source_id
        self.initial_import_days = int(self.work_items_source.parameters.get('initial_import_days', 90))
        self.sync_import_days = int(self.work_items_source.parameters.get('sync_import_days', 1))
        self.parent_path_selectors = self.work_items_source.parameters.get('parent_path_selectors')
        self.custom_tag_mapping = self.work_items_source.parameters.get('custom_tag_mapping')

        self.last_updated = work_items_source.latest_work_item_update_timestamp
        self.last_updated_issue_source_id = work_items_source.most_recently_updated_work_item_source_id

        self.jira_connector = polaris.work_tracking.connector_factory.get_connector(
            connector_key=self.work_items_source.connector_key
        )
        # map standard JIRA issue types to JiraWorkItemType enum values.
        self.custom_type_map = self.work_items_source.parameters.get('custom_type_map', {})
        self.work_item_type_map = {
            'story': JiraWorkItemType.story.value,
            'bug': JiraWorkItemType.bug.value,
            'epic': JiraWorkItemType.epic.value,
            'task': JiraWorkItemType.task.value,
            'sub-task': JiraWorkItemType.sub_task.value,
            'subtask': JiraWorkItemType.sub_task.value
        }

    def map_work_item_type(self, issue_type_to_map):
        issue_type = issue_type_to_map.lower()
        # we return story as the default value of the type
        return self.work_item_type_map.get(issue_type, JiraWorkItemType.story.value)


    def is_custom_type(self, issue_type):
        return issue_type.lower() not in self.work_item_type_map

    @staticmethod
    def jira_time_to_utc_time_string(jira_time_string):
        try:
            return datetime.strftime(
                datetime.fromtimestamp(JiraProject.parse_jira_time_string(jira_time_string).timestamp()),
                "%Y-%m-%dT%H:%M:%S.%f%z"
            )
        except ValueError as exc:
            logger.warning(f"Jira timestamp {jira_time_string} "
                           f"could not be parsed to UTC returning the original string instead.")
            return jira_time_string

    @staticmethod
    def parse_jira_time_string(jira_time_string):
        return datetime.strptime(jira_time_string, "%Y-%m-%dT%H:%M:%S.%f%z")

    @staticmethod
    def jira_time_string(timestamp):
        return timestamp.strftime("%Y-%m-%d %H:%M")

    def get_custom_parent_key(self, issue):
        for parent_path in self.parent_path_selectors:
            parent_key = jmespath.search(parent_path, issue)
            if parent_key is not None:
                return parent_key


    def map_issue_to_work_item_data(self, issue):
        if issue is not None:
            fields = issue.get('fields')
            if fields is not None:
                if 'issuetype' in fields:
                    issue_type = fields.get('issuetype').get('name')
                else:
                    raise ProcessingException(f"Expected field 'issuetype' was not found in issue {issue}")

                parent_source_display_id = self.resolve_parent_source_key(issue)

                mapped_type = self.map_work_item_type(issue_type)

                #Get story points info
                story_points = None
                story_point_link = find(self.work_items_source.custom_fields, lambda field: field['name'] == 'Story Points')
                if story_point_link is not None:
                    story_point_custom_field = story_point_link.get('key')
                    if story_point_custom_field in fields:
                        story_points =  fields.get(story_point_custom_field)

                if story_points is None:
                    story_point_link = find(self.work_items_source.custom_fields,
                                            lambda field: field['name'] == 'Story point estimate')
                    if story_point_link is not None:
                        story_point_custom_field = story_point_link.get('key')
                        if story_point_custom_field in fields:
                            story_points = fields.get(story_point_custom_field)

                #Get Release information
                version_list = fields.get('fixVersions')
                versions = []
                if version_list is not None:
                    for version in version_list:
                        versions.append(str(version))


                mapped_data = dict(
                    name=fields.get('summary'),
                    description=fields.get('description'),
                    work_item_type=mapped_type,
                    is_bug=mapped_type == JiraWorkItemType.bug.value,
                    is_epic=mapped_type == JiraWorkItemType.epic.value,
                    tags=self.process_tags(issue, fields, issue_type),
                    url=issue.get('self'),
                    source_id=str(issue.get('id')),
                    source_display_id=issue.get('key'),
                    source_last_updated=self.jira_time_to_utc_time_string(fields.get('updated')),
                    source_created_at=self.jira_time_to_utc_time_string(fields.get('created')),
                    source_state=fields.get('status').get('name'),
                    priority=fields.get('priority').get('name'),

                    parent_source_display_id=parent_source_display_id,
                    api_payload=issue,
                    commit_identifiers=[issue.get('key'), issue.get('key').lower(), issue.get('key').capitalize()],
                    releases=versions,
                    story_points=story_points
                )

                return mapped_data
            else:
                raise ProcessingException(f"Map Jira issue failed: Issue did not have field called 'fields' {issue}")
        else:
            raise ProcessingException("Map Jira issue failed: Issue was None")

    def resolve_parent_source_key(self, issue):
        fields = issue.get('fields')

        # see if we have configured custom path lookups - these override the default
        # mechanism for parent selection.
        if self.parent_path_selectors is not None:
            parent_link =  self.get_custom_parent_key(issue)
            if parent_link is not None:
                return parent_link

        # see if we can get the parent link directly.
        parent_link = fields.get('parent')  # We have parent in next-gen project issue fields
        if parent_link:
            return parent_link.get('key')

        # See if we can get it from the epic link custom field - Jira classic projects.
        parent_link = find(self.work_items_source.custom_fields, lambda field: field['name'] == 'Epic Link')
        if parent_link:
            parent_link_custom_field = parent_link.get('key')
            if parent_link_custom_field in fields:
                return fields.get(parent_link_custom_field)

    def process_tags(self, issue, fields, issue_type):
        def apply_custom_tags(issue, tags):
            def map_path_selector_tag(issue, mapping, tags):
                path_selector_mapping = mapping.get('path_selector_mapping')
                if path_selector_mapping is not None:
                    if 'selector' in path_selector_mapping and jmespath.search(path_selector_mapping['selector'],
                                                                               issue) is not None:
                        tags.add(f"custom_tag:{path_selector_mapping.get('tag')}")

            def map_custom_field_populated_tag(issue, mapping, tags):
                custom_field_mapping = mapping.get('custom_field_mapping')
                if custom_field_mapping is not None:
                    if 'field_name' in custom_field_mapping:
                        field = find(self.work_items_source.custom_fields,
                                     lambda field: field['name'] == custom_field_mapping['field_name'])
                        if field is not None and 'id' in field:
                            value = issue['fields'].get(field['id'])
                            if value is not None:
                                tags.add(f"custom_tag:{custom_field_mapping.get('tag')}")

            if self.custom_tag_mapping is not None:
                for mapping in self.custom_tag_mapping:
                    if mapping.get('mapping_type') == CustomTagMappingType.path_selector.value:
                        map_path_selector_tag(issue, mapping, tags)
                    elif mapping.get('mapping_type') == CustomTagMappingType.custom_field_populated.value:
                        map_custom_field_populated_tag(issue, mapping, tags)

                    else:
                        logger.warning(
                            f"Unknown custom tag mapping type {mapping.get('mapping_type')} found when mapping custom tags for Jira work items source")

        tags = set(fields.get('labels', []))
        if self.is_custom_type(issue_type):
            tags.add(f'custom_type:{issue_type}')
        # lift the components into tags
        for component in fields.get('components', []):
            tags.add(f"component:{component['name']}")

        #apply any custom tag mappers
        apply_custom_tags(issue, tags)

        return list(tags)



    def get_server_timezone_offset(self):
        # This is an awful hack to get around Jira APIs
        # completely boneheaded implementation of time based querying.
        # Since they dont allow specifying timezones in the JQL, we have to
        # guess what timezone they want. /serverinfo is supposed to give us
        # a reference timestamp, but it does not recognize JWT authentication which we
        # use, so what we are doing here is to fetch the issue that was last updated
        # from our perspective and get the updated_at date on that issue to see what the
        # timezone of that date is. It is a truly awful solution, but POS products like Jira force
        # us to do awful things.
        if self.last_updated_issue_source_id is not None:
            response = self.jira_connector.get(
                f'/issue/{self.last_updated_issue_source_id}',
                headers={"Accept": "application/json"}
            )
            if response.ok:
                result = response.json()
                if result is not None:
                    last_updated = JiraProject.parse_jira_time_string(result['fields']['updated'])

                    return last_updated.utcoffset()

    def fetch_work_items_to_sync(self):
        logger.info(f"Sync work items for Jira Connector {self.jira_connector.key}")
        jql_base = f"project = {self.project_id} "

        if self.work_items_source.last_synced is None or self.last_updated is None:
            jql = f'{jql_base} AND updated >= "-{self.initial_import_days}d"'
        else:
            jql = f'{jql_base} AND updated >= "-{self.sync_import_days}d"'

        query_params = dict(
            fields="*all,-comment",
            jql=jql,
            maxResults=100
        )

        response = self.jira_connector.get(
            '/search',
            headers={"Accept": "application/json"},
            params=query_params
        )
        if response.status_code == 200:
            offset = 0
            body = response.json()
            if body is not None:
                total = int(body.get('total') or 0)
                while offset < total and response.status_code == 200:
                    issues = body.get('issues', [])
                    if len(issues) == 0:
                        break
                    work_items = []
                    for issue in issues:
                        try:
                            work_item_data = self.map_issue_to_work_item_data(issue)
                            if work_item_data:
                                work_items.append(work_item_data)
                        except ProcessingException as e:
                            logger.error(f"Failed to map issue data {e}")

                    yield work_items
                    offset = offset + len(issues)
                    query_params['startAt'] = offset
                    response = self.jira_connector.get(
                        '/search',
                        headers={"Accept": "application/json"},
                        params=query_params
                    )
                    body = response.json()
            else:
                logger.error(f'Response body was empty: Request {response.request}')

        else:
            logger.error(f"Could not fetch work items for to sync for project  {self.project_id}. Response {response.status_code} {response.text}")

        yield []

    def fetch_work_items_for_epic(self, epic):
        epic_source_id = epic['source_id']
        jql_base = f"project = {self.project_id} "
        jql = f'{jql_base} AND (parent={epic_source_id} OR \"Epic Link\" = {epic_source_id}) AND updated >= "-{self.initial_import_days}d"'

        query_params = dict(
            fields="*all,-comment",
            jql=jql,
            maxResults=100
        )

        response = self.jira_connector.get(
            '/search',
            headers={"Accept": "application/json"},
            params=query_params
        )

        if response.ok:
            offset = 0
            body = response.json()
            total = int(body.get('total') or 0)
            while offset < total and response.ok:
                issues = body.get('issues', [])
                if len(issues) == 0:
                    break
                work_items = []
                for issue in issues:
                    work_item_data = self.map_issue_to_work_item_data(issue)
                    if work_item_data:
                        work_items.append(work_item_data)

                yield work_items
                offset = offset + len(issues)
                query_params['startAt'] = offset
                response = self.jira_connector.get(
                    '/search',
                    headers={"Accept": "application/json"},
                    params=query_params
                )
                body = response.json()
        else:
            logger.error(f"Could not fetch work items for epic {epic_source_id}. Response {response.status_code} {response.text}")

        yield []

    def fetch_work_item(self, source_id):
        try:
            logger.info(f"Fetching work item with source_id {source_id}")
            jql_base = f"project = {self.project_id} "
            get_issue_query = dict(
                fields="*all, -comment",
                jql=f'{jql_base} AND key={source_id}'
            )
            response = self.jira_connector.get(
                '/search',
                headers={"Accept": "application/json"},
                params=get_issue_query
            )
            work_item_data = []
            if response.ok:
                body = response.json()
                if body is not None:
                    issues = body.get('issues', [])
                    if len(issues) > 0:
                        work_item_data = self.map_issue_to_work_item_data(issues[0])

                    else:
                        logger.error(f"Could not fetch work item with key: {source_id}: No issues were returned. Response was {body}")
                else:
                    logger.error("Null response json body returned for JQL query.")
            else:
                logger.error(f"Could not fetch work item with key {source_id}. Response: {response.status_code} {response.text}")

            return work_item_data
        except Exception as exc:
            logger.error(f"Fetch work item {source_id} failed for jira project {self.work_items_source.name}")
            raise ProcessingException(f'Unexpected error when fetching work item {source_id} from jira project: {self.work_items_source.name}')


