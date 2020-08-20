# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2016) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import pytest
from datetime import datetime

from polaris.common.test_support import dbtest_addoption
from polaris.common.test_support import init_db
from polaris.work_tracking.db import model
from polaris.integrations.db import model as integrations_model
from polaris.common import db
from test.constants import *
from polaris.common.enums import PivotalTrackerWorkItemType, GithubWorkItemType, WorkItemsSourceImportState, ConnectorProductType

pytest_addoption = dbtest_addoption


@pytest.fixture(scope='session')
def db_up(pytestconfig):
    init_db(pytestconfig)


@pytest.fixture(scope='session')
def setup_schema(db_up):
    model.recreate_all(db.engine())
    integrations_model.recreate_all(db.engine())


@pytest.yield_fixture
def setup_connectors(setup_schema):
    pivotal_connector_key = uuid.uuid4()
    github_connector_key = uuid.uuid4()

    with db.orm_session() as session:
        session.expire_on_commit = False
        session.add(
            integrations_model.PivotalTracker(
                key=pivotal_connector_key,
                name='test-pivotal-connector',
                base_url='https://www.pivotaltracker.com',
                account_key=exathink_account_key,
                state='enabled',
                api_key='foobar'
            )
        )
        session.add(
            integrations_model.Github(
                key=github_connector_key,
                name='test-github-connector',
                base_url='https://api.github.com',
                account_key=exathink_account_key,
                github_organization='exathink',
                oauth_access_token='foobar',
                product_type=ConnectorProductType.github_oauth_token.value,
                state='enabled'
            )
        )


    yield dict(
        pivotal=pivotal_connector_key,
        github=github_connector_key
    )


@pytest.yield_fixture()
def setup_work_item_sources(setup_schema, setup_connectors):
    connector_keys = setup_connectors
    work_items_sources = {}
    with db.orm_session() as session:
        session.expire_on_commit = False
        work_items_sources['github'] = model.WorkItemsSource(
            key=rails_work_items_source_key,
            integration_type='github',
            work_items_source_type='repository_issues',
            parameters=dict(repository='rails', organization='rails'),
            name='rails repository issues',
            account_key=exathink_account_key,
            organization_key=rails_organization_key,
            commit_mapping_scope='organization',
            commit_mapping_scope_key=rails_organization_key,
            import_state=WorkItemsSourceImportState.ready.value
        )
        work_items_sources['pivotal'] = model.WorkItemsSource(
            key=polaris_work_items_source_key,
            connector_key=connector_keys['pivotal'],
            integration_type='pivotal_tracker',
            work_items_source_type='project',
            parameters=dict(id="1934657", name="polaris-web"),
            name='polaris-web',
            account_key=exathink_account_key,
            organization_key=polaris_organization_key,
            commit_mapping_scope='organization',
            commit_mapping_scope_key=polaris_organization_key,
            import_state=WorkItemsSourceImportState.ready.value
        )
        # This will have no work_items set up initially
        work_items_sources['empty'] = model.WorkItemsSource(
            key=empty_work_items_source_key,
            connector_key=connector_keys['pivotal'],
            integration_type='pivotal_tracker',
            work_items_source_type='project',
            parameters=dict(id="1934657", name="polaris-web"),
            name='polaris-web2',
            account_key=exathink_account_key,
            organization_key=polaris_organization_key,
            commit_mapping_scope='organization',
            commit_mapping_scope_key=polaris_organization_key,
            import_state=WorkItemsSourceImportState.ready.value
        )

        session.add_all(work_items_sources.values())
        session.flush()
        yield session, work_items_sources


@pytest.yield_fixture()
def setup_work_items(setup_work_item_sources, cleanup):
    session, work_items_sources = setup_work_item_sources
    work_items = []
    with db.orm_session(session) as session:
        work_items.extend(setup_github_work_items(work_items_sources['github']))
        work_items.extend(setup_pivotal_work_items(work_items_sources['pivotal']))
        session.flush()

    yield work_items, work_items_sources


def setup_github_work_items(work_item_source):
    for display_id in range(1000, 1010):
        work_item_source.work_items.append(
            model.WorkItem(
                key=uuid.uuid4(),
                name=f"Issue {display_id}",
                description="An issue in detail",
                work_item_type=GithubWorkItemType.issue.value,
                is_bug=False,
                is_epic=False,
                tags=[],
                source_id=str(display_id),
                source_display_id=str(display_id),
                source_state='',
                url='',
                source_created_at=datetime.utcnow(),
                source_last_updated=datetime.utcnow(),
                last_sync=datetime.utcnow()
            )
        )

    return work_item_source.work_items


def setup_pivotal_work_items(work_item_source):
    for display_id in range(2000, 2010):
        work_item_source.work_items.append(
            model.WorkItem(
                key=uuid.uuid4(),
                name=f"Story {display_id}",
                work_item_type=PivotalTrackerWorkItemType.story.value,
                is_bug=False,
                is_epic=False,
                tags=[],
                source_id=str(display_id),
                source_display_id=str(display_id),
                source_state='',
                url='',
                source_created_at=datetime.utcnow(),
                source_last_updated=datetime.utcnow(),
                last_sync=datetime.utcnow()
            )
        )

    return work_item_source.work_items


work_items_common = dict(
    work_item_type=GithubWorkItemType.issue.value,
    description='Foo',
    is_bug=True,
    is_epic=False,
    tags=['acre'],
    source_last_updated=datetime.utcnow(),
    source_created_at=datetime.utcnow(),
    source_state='open'
)


@pytest.fixture
def new_work_items():
    return [
        dict(
            name=f'Issue {i}',
            source_id=str(i),
            source_display_id=str(i),
            url=f'http://foo.com/{i}',
            **work_items_common
        )
        for i in range(100, 110)
    ]


@pytest.yield_fixture
def cleanup():
    yield
    db.connection().execute(f"delete from work_tracking.work_items")
    db.connection().execute(f"delete from work_tracking.work_items_sources")


    db.connection().execute(f"delete from integrations.connectors")
