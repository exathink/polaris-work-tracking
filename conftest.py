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
from polaris.common import db
from test.constants import *

pytest_addoption = dbtest_addoption


@pytest.fixture(scope='session')
def db_up(pytestconfig):
    init_db(pytestconfig)


@pytest.fixture(scope='session')
def setup_schema(db_up):
    model.recreate_all(db.engine())


@pytest.yield_fixture(scope='session')
def setup_work_item_sources(setup_schema):
    work_items_sources = {}
    with db.orm_session() as session:
        session.expire_on_commit=False
        work_items_sources['github'] = model.WorkItemsSource(
            key=rails_work_items_source_key,
            integration_type='github',
            work_items_source_type='repository_issues',
            parameters=dict(repository='rails', organization='rails'),
            name='rails repository issues',
            account_key=exathink_account_key,
            organization_key=rails_organization_key,
            repository_key=rails_repository_key
        )
        work_items_sources['pivotal'] = model.WorkItemsSource(
            key=polaris_work_items_source_key,
            integration_type='pivotal_tracker',
            work_items_source_type='project',
            parameters=dict(id="1934657", name="polaris-web"),
            name='polaris-web',
            account_key=exathink_account_key,
            organization_key=polaris_organization_key,
            repository_key=None
        )
        # This will have no work_items set up initially
        work_items_sources['empty'] = model.WorkItemsSource(
            key=empty_work_items_source_key,
            integration_type='pivotal_tracker',
            work_items_source_type='project',
            parameters=dict(id="1934657", name="polaris-web"),
            name='polaris-web2',
            account_key=exathink_account_key,
            organization_key=polaris_organization_key,
            repository_key=None
        )

        session.add_all(work_items_sources.values())
        session.flush()
        yield session, work_items_sources

@pytest.yield_fixture(scope='session')
def setup_work_items(setup_work_item_sources):
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
                is_bug=False,
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
                is_bug=False,
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
    description='Foo',
    is_bug=True,
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
def cleanup_empty(setup_work_items):
    yield
    _, work_items_sources = setup_work_items
    db.connection().execute(f"delete from work_tracking.work_items where work_items_source_id={work_items_sources['empty'].id}")


