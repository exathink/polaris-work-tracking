# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar

import uuid
import logging
from polaris.common import db
from .model import WorkItem, WorkItemsSource, work_items, work_items_sources, cached_commits, work_items_commits as work_items_commits_table
from sqlalchemy import select, and_, literal_column, Column, BigInteger, text
from sqlalchemy.dialects.postgresql import insert, UUID

logger = logging.getLogger('polaris.work_tracker.db.api')


def sync_work_items(work_items_source_key, work_item_list, join_this=None):
    rows = 0
    if len(work_item_list) > 0:
        with db.orm_session(join_this) as session:
            work_items_source = WorkItemsSource.find_by_work_items_source_key(session, work_items_source_key)
            work_items_temp = db.temp_table_from(
                work_items,
                table_name='work_items_temp',
                exclude_columns=[work_items.c.id]
            )
            work_items_temp.create(session.connection(), checkfirst=True)

            upsert = insert(work_items).values([
                dict(
                    key=uuid.uuid4(),
                    work_items_source_id=work_items_source.id,
                    **work_item
                )
                for work_item in work_item_list
            ]
            )

            rows = session.connection().execute(
                upsert.on_conflict_do_update(
                    index_elements=['work_items_source_id','source_id'],
                    set_=dict(
                        name=upsert.excluded.name,
                        description=upsert.excluded.description,
                        is_bug=upsert.excluded.is_bug,
                        tags=upsert.excluded.tags,
                        url=upsert.excluded.url,
                        source_last_updated=upsert.excluded.source_last_updated,
                        source_display_id=upsert.excluded.source_display_id,
                        source_state=upsert.excluded.source_state
                    )
                )
            ).rowcount

    return rows

def update_work_items_commits(organization_key, repository_name, work_items_commits):
    with db.create_session() as session:
        wc_temp = db.temp_table_from(
            cached_commits,
            table_name='work_item_commits_temp',
            exclude_columns=[cached_commits.c.id],
            extra_columns=[
                Column('work_item_key', UUID(as_uuid=True)),
                Column('commit_id', BigInteger)
            ]
        )
        wc_temp.create(session.connection, checkfirst=True)

        # insert tuples in form (work_item_key, commit_header*) into the temp table.
        # the same commit might appear more than once in this table.
        session.connection.execute(
            wc_temp.insert([
                dict(
                    work_item_key=work_item['work_item_key'],
                    repository_name=repository_name,
                    **commit_header
                )
                for work_item in work_items_commits
                for commit_header in work_item['commit_headers']
            ])
        )
        # extract distinct commits that dont exist in the cached_commits table
        # and insert them
        session.connection.execute(
            cached_commits.insert().from_select(
                [
                    'commit_key',
                    'repository_name',
                    'commit_date',
                    'commit_date_tz_offset',
                    'committer_contributor_name',
                    'committer_contributor_key',
                    'author_date',
                    'author_date_tz_offset',
                    'author_contributor_name',
                    'author_contributor_key',
                    'commit_message',
                    'created_on_branch'
                ],
                select(
                    [
                        wc_temp.c.commit_key,
                        wc_temp.c.repository_name,
                        wc_temp.c.commit_date,
                        wc_temp.c.commit_date_tz_offset,
                        wc_temp.c.committer_contributor_name,
                        wc_temp.c.committer_contributor_key,
                        wc_temp.c.author_date,
                        wc_temp.c.author_date_tz_offset,
                        wc_temp.c.author_contributor_name,
                        wc_temp.c.author_contributor_key,
                        wc_temp.c.commit_message,
                        wc_temp.c.created_on_branch
                    ]
                ).distinct().select_from(
                    wc_temp.outerjoin(
                        cached_commits,
                        and_(
                            wc_temp.c.commit_key == cached_commits.c.commit_key,
                            wc_temp.c.repository_name == cached_commits.c.repository_name
                        )
                    )
                ).where(
                    cached_commits.c.id == None
                )
            )
        )

        # Copy over the commit ids of all commits we are importing into the wc_temp table.
        session.connection.execute(
            wc_temp.update().values(
                commit_id=select([
                    cached_commits.c.id.label('commit_id')
                ]).where(
                    and_(
                        cached_commits.c.repository_name == wc_temp.c.repository_name,
                        cached_commits.c.commit_key == wc_temp.c.commit_key
                    )
                ).limit(1)
            )
        )


        # Now insert the work_item_commits relationships ignoring any that might already exist.
        insert_stmt = insert(work_items_commits_table).from_select(
                ['work_item_id', 'commit_id'],
                select(
                    [
                        work_items.c.id.label('work_item_id'),
                        wc_temp.c.commit_id
                    ]
                ).select_from(
                    work_items.join(
                        wc_temp, wc_temp.c.work_item_key == work_items.c.key
                    )
                )

            )

        session.connection.execute(
            insert_stmt.on_conflict_do_nothing(
                index_elements=['work_item_id', 'commit_id']
            )
        )




def resolve_work_items_by_display_ids(organization_key, display_ids):
    resolved = {}
    if len(display_ids) > 0:
        with db.create_session() as session:
            resolved = {
                work_item['display_id']: dict(
                    key=work_item.key,
                    display_id=work_item.display_id,
                    url=work_item.url,
                    name=work_item.name,
                    work_items_source_key=work_item.work_items_source_key
                )
                for work_item in session.connection.execute(
                    select([
                        work_items.c.key,
                        work_items.c.source_display_id.label('display_id'),
                        work_items.c.url,
                        work_items.c.name,
                        work_items_sources.c.key.label('work_items_source_key'),
                    ]).select_from(
                        work_items.join(work_items_sources, work_items.c.work_items_source_id == work_items_sources.c.id)
                    ).where(
                        and_(
                            work_items_sources.c.organization_key == organization_key,
                            work_items.c.source_display_id.in_(display_ids)
                        )
                    )
                ).fetchall()
            }

    return resolved