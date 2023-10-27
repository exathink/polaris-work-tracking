# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

from polaris.common import db
from polaris.work_tracking.db import api
from .fixtures.jira_fixtures import *
from polaris.utils.collections import object_to_dict, Fixture


class TestSyncWorkItems:

    def it_imports_work_items_when_the_source_has_no_work_items(self, setup_work_items, new_work_items):
        _, work_items_sources = setup_work_items
        empty_source = work_items_sources['empty']
        created = api.sync_work_items(empty_source.key, work_item_list=new_work_items)
        assert len(created) == len(new_work_items)
        assert db.connection().execute(
            f"select count(id) from work_tracking.work_items where work_items_source_id={empty_source.id}"
        ).scalar() == len(new_work_items)

    def it_updates_existing_work_items_that_match_incoming_items_by_source_id(self, setup_work_items, new_work_items):
        _, work_items_sources = setup_work_items
        empty_source = work_items_sources['empty']
        # Import once
        api.sync_work_items(empty_source.key, work_item_list=new_work_items)
        # Now import updated versions of the same source work items
        created = api.sync_work_items(empty_source.key, work_item_list=[
            {**work_item, **dict(source_state='closed')}
            for work_item in new_work_items
        ])
        assert len(created) == 10
        assert db.connection().execute(
            f"select count(id) from work_tracking.work_items where work_items_source_id={empty_source.id} and source_state='closed'"
        ).scalar() == len(new_work_items)

    def it_updates_work_item_type_for_an_existing_work_item(self, setup_work_items, new_work_items):
        _, work_items_sources = setup_work_items
        empty_source = work_items_sources['empty']
        # Import once
        api.sync_work_items(empty_source.key, work_item_list=new_work_items)
        # Now import updated versions of the same source work items
        created = api.sync_work_items(empty_source.key, work_item_list=[
            {**work_item, **dict(work_item_type='enhancement')}
            for work_item in new_work_items
        ])
        assert len(created) == 10
        assert db.connection().execute(
            f"select count(id) from work_tracking.work_items where work_items_source_id={empty_source.id} and work_item_type='enhancement' and is_bug=true"
        ).scalar() == len(new_work_items)

    def it_returns_updated_elements_for_those_that_match_existing_items_by_source_id(self, setup_work_items,
                                                                                     new_work_items):
        _, work_items_sources = setup_work_items
        empty_source = work_items_sources['empty']
        # Import once
        api.sync_work_items(empty_source.key, work_item_list=new_work_items)
        # Now import the same set again
        result = api.sync_work_items(empty_source.key, work_item_list=new_work_items)
        assert len(result) == 10
        assert db.connection().execute(
            f"select count(id) from work_tracking.work_items where work_items_source_id={empty_source.id}"
        ).scalar() == len(new_work_items)







class TestSyncWorkItem:

    def it_creates_a_new_work_item(self, setup_work_items, new_work_items):
        _, work_items_sources = setup_work_items
        empty_source = work_items_sources['empty']
        # Import once
        result = api.sync_work_item(empty_source.key, work_item_data=new_work_items[0])[0]
        assert result['is_new']
        assert result['name'] == new_work_items[0]['name']
        assert db.connection().execute(
            f"select count(id) from work_tracking.work_items where work_items_source_id={empty_source.id} and key='{result['key']}'"
        ).scalar() == 1

    def it_returns_the_fields_that_need_to_be_sent_out_to_analytics(self, setup_work_items, new_work_items):
        _, work_items_sources = setup_work_items
        empty_source = work_items_sources['empty']
        # Import once
        field_list = [
                      "is_new",
                      "key",
                      "work_items_source_key",
                      "work_item_type",
                      "display_id",
                      "url",
                      "name",
                      "description",
                      "is_bug",
                      "is_epic",
                      "parent_source_display_id",
                      "tags",
                      "created_at",
                      "updated_at",
                      "last_sync",
                      "source_id",
                      "commit_identifiers",
                      "is_updated",
                      "priority",
                      "releases",
                      "story_points",
                      "sprints",
                      "flagged"
                      ]

        result = api.sync_work_item(empty_source.key, work_item_data=new_work_items[0])[0]
        for field in field_list:
            assert field in result





    def it_updates_a_work_item_without_epic_info(self, setup_work_items, new_work_items):
        _, work_items_sources = setup_work_items
        empty_source = work_items_sources['empty']
        # Import once
        api.sync_work_items(empty_source.key, work_item_list=new_work_items)
        updated_work_item = new_work_items[0]
        updated_work_item['source_state'] = 'closed'
        updated_work_item['priority'] = 'Medium'
        result = api.sync_work_item(empty_source.key, work_item_data=updated_work_item)[0]
        assert result['is_updated']
        assert db.connection().execute(
            f"select count(id) from work_tracking.work_items where work_items_source_id={empty_source.id} and key='{result['key']}' and source_state='closed' and priority='Medium'"
        ).scalar() == 1

    def it_updates_epic_id_when_epic_work_item_exists(self, setup_work_items, new_work_items):
        _, work_items_sources = setup_work_items
        empty_source = work_items_sources['empty']
        # Import once
        new_work_items[-1]['is_epic'] = True
        api.sync_work_items(empty_source.key, work_item_list=new_work_items)
        updated_work_item = new_work_items[0]
        updated_work_item['parent_source_display_id'] = new_work_items[-1]['source_display_id']
        updated_work_item['priority'] = 'Medium'
        result = api.sync_work_item(empty_source.key, work_item_data=updated_work_item)[0]
        assert result['is_updated']
        assert db.connection().execute(
            f"select count(id) from work_tracking.work_items where work_items_source_id={empty_source.id} and key='{result['key']}' and parent_id is not NULL and priority = 'Medium'"
        ).scalar() == 1

    def it_does_not_update_epic_id_when_epic_work_item_does_not_exist(self, setup_work_items, new_work_items):
        _, work_items_sources = setup_work_items
        empty_source = work_items_sources['empty']
        # Import once
        api.sync_work_items(empty_source.key, work_item_list=new_work_items)
        updated_work_item = new_work_items[0]
        updated_work_item['parent_source_display_id'] = 'Does not exist'
        result = api.sync_work_item(empty_source.key, work_item_data=updated_work_item)[0]

        assert db.connection().execute(
            f"select count(id) from work_tracking.work_items where work_items_source_id={empty_source.id} and key='{result['key']}' and parent_id is NULL"
        ).scalar() == 1


class TestMoveWorkItem:
    class TestWhenSourceAndTargetWorkItemsSourcesArePresent:

        @pytest.fixture()
        def setup(self, jira_work_items_fixture, cleanup):
            work_items, work_items_source, jira_project_id, connector_key = jira_work_items_fixture
            # create a new work items source
            with db.orm_session() as session:
                session.expire_on_commit = False
                target_work_items_source = work_tracking.WorkItemsSource(
                    key=uuid.uuid4(),
                    connector_key=str(connector_key),
                    integration_type='jira',
                    work_items_source_type=JiraWorkItemSourceType.project.value,
                    name='Test Project 2',
                    source_id='10002',
                    parameters=dict(),
                    account_key=account_key,
                    organization_key=organization_key,
                    commit_mapping_scope='organization',
                    import_state=WorkItemsSourceImportState.auto_update.value,
                    custom_fields=[{"id": "customfield_10014", "key": "customfield_10014", "name": "Epic Link"}]
                )
                session.add(target_work_items_source)
                session.flush()

            yield Fixture(
                work_items=work_items,
                source_work_items_source=work_items_source,
                target_work_items_source=target_work_items_source
            )

        def it_updates_work_item_work_items_source_when_target_is_active(self, setup):
            fixture = setup
            work_item = [wi for wi in fixture.work_items if not wi.is_epic][0]
            updated_work_item = object_to_dict(
                work_item,
                ['name',
                 'description',
                 'work_item_type',
                 'is_bug',
                 'is_epic',
                 'tags',
                 'source_id',
                 'source_display_id',
                 'source_state',
                 'url',
                 'source_created_at',
                 'source_last_updated',
                 'parent_id',
                 'api_payload',
                 'commit_identifiers'
                 ],
                {
                    'parent_id': 'parent_source_display_id'
                }
            )
            updated_work_item['source_display_id'] = 'TP2-1'
            updated_work_item['commit_identifiers'] = ["TP2-1", "Tp2-1", "tp2-1"]
            result = api.move_work_item(fixture.source_work_items_source.key, fixture.target_work_items_source.key,
                                        updated_work_item)
            assert result
            assert result['is_moved']
            assert db.connection().execute(
                f"select count(id) from work_tracking.work_items where work_items_source_id={fixture.source_work_items_source.id} and source_id='{updated_work_item['source_id']}'"
            ).scalar() == 0
            assert db.connection().execute(
                f"select count(id) from work_tracking.work_items where work_items_source_id={fixture.target_work_items_source.id} and source_id='{updated_work_item['source_id']}'"
                f" and source_display_id='TP2-1' and commit_identifiers='[\"TP2-1\", \"Tp2-1\", \"tp2-1\"]'").scalar() == 1

        def it_updates_work_item_is_moved_to_true_when_target_is_in_ready_state(self, setup):
            fixture = setup
            with db.orm_session() as session:
                target_work_items_source = fixture.target_work_items_source
                target_work_items_source.import_state = WorkItemsSourceImportState.ready.value
                session.add(target_work_items_source)
            work_item = [wi for wi in fixture.work_items if not wi.is_epic][0]
            updated_work_item = object_to_dict(
                work_item,
                ['name',
                 'description',
                 'work_item_type',
                 'is_bug',
                 'is_epic',
                 'tags',
                 'source_id',
                 'source_display_id',
                 'source_state',
                 'url',
                 'source_created_at',
                 'source_last_updated',
                 'parent_id',
                 'api_payload',
                 'commit_identifiers'
                 ],
                {
                    'parent_id': 'parent_source_display_id'
                }
            )
            updated_work_item['source_display_id'] = 'TP2-1'
            updated_work_item['is_moved'] = True
            updated_work_item['commit_identifiers'] = ["TP2-1", "Tp2-1", "tp2-1"]
            result = api.move_work_item(fixture.source_work_items_source.key, None,
                                        updated_work_item)
            assert result
            assert result['is_moved']

        def it_does_not_change_parent_when_work_item_is_moved_to_different_source(self, setup):
            fixture = setup
            work_item = [wi for wi in fixture.work_items if not wi.is_epic][0]
            epic = [wi for wi in fixture.work_items if wi.is_epic][0]
            with db.orm_session() as session:
                work_item.parent_id = epic.id
                work_item.parent_source_display_id = epic.source_display_id
                session.add(work_item)
            updated_work_item = object_to_dict(
                work_item,
                ['name',
                 'description',
                 'work_item_type',
                 'is_bug',
                 'is_epic',
                 'tags',
                 'source_id',
                 'source_display_id',
                 'source_state',
                 'url',
                 'source_created_at',
                 'source_last_updated',
                 'parent_id',
                 'api_payload',
                 'commit_identifiers'
                 ],
                {
                    'parent_id': 'parent_source_display_id'
                }
            )
            updated_work_item['parent_source_display_id'] = epic.source_display_id
            updated_work_item['source_display_id'] = 'TP2-1'
            updated_work_item['commit_identifiers'] = ["TP2-1", "Tp2-1", "tp2-1"]
            result = api.move_work_item(fixture.source_work_items_source.key, fixture.target_work_items_source.key,
                                        updated_work_item)
            assert result
            assert result['is_moved']
            assert db.connection().execute(
                f"select count(id) from work_tracking.work_items where work_items_source_id={fixture.source_work_items_source.id} and source_id='{updated_work_item['source_id']}'"
            ).scalar() == 0
            assert db.connection().execute(
                f"select count(id) from work_tracking.work_items where work_items_source_id={fixture.target_work_items_source.id} and source_id='{updated_work_item['source_id']}'"
                f" and source_display_id='TP2-1' and commit_identifiers='[\"TP2-1\", \"Tp2-1\", \"tp2-1\"]' and parent_id={epic.id}").scalar() == 1

    class TestWhenSourceExistsTargetDoesNot:

        @pytest.fixture()
        def setup(self, jira_work_items_fixture, cleanup):
            work_items, work_items_source, jira_project_id, connector_key = jira_work_items_fixture

            yield Fixture(
                work_items=work_items,
                source_work_items_source=work_items_source
            )

        def it_updates_work_item_to_a_moved_state(self, setup):
            fixture = setup
            work_item = [wi for wi in fixture.work_items if not wi.is_epic][0]
            updated_work_item = object_to_dict(
                work_item,
                ['name',
                 'description',
                 'work_item_type',
                 'is_bug',
                 'is_epic',
                 'tags',
                 'source_id',
                 'source_display_id',
                 'source_state',
                 'url',
                 'source_created_at',
                 'source_last_updated',
                 'parent_id',
                 'api_payload',
                 'commit_identifiers'
                 ],
                {
                    'parent_id': 'parent_source_display_id'
                }
            )
            updated_work_item['source_display_id'] = 'TP2-1'
            updated_work_item['is_moved'] = True
            updated_work_item['commit_identifiers'] = ["TP2-1", "Tp2-1", "tp2-1"]
            result = api.move_work_item(fixture.source_work_items_source.key, None,
                                        updated_work_item)
            assert result
            assert result['is_moved']

    class TestWhenTargetExistsSourceDoesNot:

        @pytest.fixture()
        def setup(self, jira_work_items_fixture, cleanup):
            work_items, work_items_source, jira_project_id, connector_key = jira_work_items_fixture

            yield Fixture(
                work_items=work_items,
                target_work_items_source=work_items_source
            )

        def it_creates_new_work_item(self, setup):
            fixture = setup
            source_id = '10001'
            moved_work_item = dict(
                name=f'Issue 1',
                source_id=source_id,
                source_display_id=f'PRJ-{source_id}',
                url=f'http://foo.com/{source_id}',
                work_item_type=JiraWorkItemType.task.value,
                description='Foo',
                is_bug=False,
                is_epic=False,
                tags=['acre'],
                source_last_updated=datetime.utcnow(),
                source_created_at=datetime.utcnow(),
                source_state='open'
            )

            moved_work_item['source_display_id'] = 'TP2-1'
            moved_work_item['commit_identifiers'] = ["TP2-1", "Tp2-1", "tp2-1"]
            result = api.sync_work_item(fixture.target_work_items_source.key,
                                        moved_work_item)[0]
            assert result
            assert result['is_new']
