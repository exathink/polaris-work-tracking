# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar



import uuid
import logging

logger = logging.getLogger('polaris.work_tracking.db.model')

from sqlalchemy import \
    Table, Index, Column, BigInteger, Integer, String, Text, DateTime, \
    Boolean, MetaData, ForeignKey, TIMESTAMP, and_, UniqueConstraint



from sqlalchemy.orm import relationship, object_session
from sqlalchemy.sql import cast, select, func

from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from polaris.common import db

Base = db.polaris_declarative_base(metadata=MetaData(schema='work_tracking'))


# many-many relationship table
work_items_commits = Table(
    'work_items_commits', Base.metadata,
    Column('work_item_id', ForeignKey('work_items.id'), primary_key=True, index=True),
    Column('commit_id', ForeignKey('cached_commits.id'), primary_key=True, index=True)
)


class WorkItemsSource(Base):
    __tablename__ = 'work_items_sources'

    id = Column(Integer, primary_key=True)
    key =  Column(UUID(as_uuid=True), nullable=False, unique=True)
    # type of integration: github, github_enterprise, jira, pivotal_tracker etc..
    integration_type = Column(String, nullable=False)

    # integration specific sub type: for example github_repository_issues, github_organization_issues
    # this type determines the shape of the expected parameters for an instance of the WorkItemsSource
    work_items_source_type = Column(String(128), nullable=False)
    parameters = Column(JSONB, nullable=True, default={}, server_default='{}')
    # User facing display name for the instance.
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    # An instance must be tied to an account at the very least.
    account_key = Column(UUID(as_uuid=True), nullable=False)
    organization_key = Column(UUID(as_uuid=True), nullable=False)
    # Optionally, it can be tied to a project and/or a specific repository.
    project_key = Column(UUID(as_uuid=True), nullable=True)
    repository_key = Column(UUID(as_uuid=True), nullable=True)

    work_items = relationship('WorkItem')


    @classmethod
    def find_by_organization_key(cls, session, organization_key):
        return session.query(cls).filter(cls.organization_key == organization_key).all()


    @classmethod
    def find_by_work_items_source_key(cls, session, work_items_source_key):
        return session.query(cls).filter(cls.key == work_items_source_key).first()

    @property
    def latest_work_item_creation_date(self):
        return object_session(self).scalar(
            select([func.max(work_items.c.source_created_at)]).where(
                work_items.c.work_items_source_id == self.id
            )
        )

    @property
    def latest_work_item_update_timestamp(self):
        return object_session(self).scalar(
            select([func.max(work_items.c.source_last_updated)]).where(
                work_items.c.work_items_source_id == self.id
            )
        )


    def find_work_items_by_source_id(self, session, source_ids):
        return session.query(WorkItem).filter(
            and_(
                work_items.c.work_items_source_id == self.id,
                work_items.c.source_id.in_(source_ids)
            )
        )


work_items_sources = WorkItemsSource.__table__


class WorkItem(Base):
    __tablename__ = 'work_items'

    id = Column(BigInteger, primary_key=True)
    key = Column(UUID(as_uuid=True), nullable=False, unique=True)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    is_bug = Column(Boolean, nullable=False, default=False, server_default='FALSE')
    tags = Column(ARRAY(String), nullable=False, default=[], server_default='{}')
    # ID of the item in the source system, used to cross ref this instance for updates etc.
    source_id = Column(String, nullable=True)
    url=Column(String, nullable=True)
    source_created_at=Column(DateTime, nullable=False)
    source_last_updated = Column(DateTime, nullable=True)
    source_display_id = Column(String, nullable=False)
    source_state=Column(String, nullable=False)
    last_sync=Column(DateTime, nullable=True)
    # Work Items Source relationship
    work_items_source_id = Column(Integer, ForeignKey('work_items_sources.id'))
    work_items_source = relationship('WorkItemsSource', back_populates='work_items')
    commits = relationship("CachedCommit",
                                 secondary=work_items_commits,
                                 back_populates="work_items")


work_items = WorkItem.__table__
Index('ix_work_items_work_item_source_id_source_display_id', work_items.c.work_items_source_id, work_items.c.source_display_id)
UniqueConstraint(work_items.c.work_items_source_id, work_items.c.source_id)


class CachedCommit(Base):
    __tablename__ = 'cached_commits'

    id = Column(BigInteger, primary_key=True)
    commit_key = Column(String, nullable=False)
    repository_name = Column(String, nullable=False)
    organization_key = Column(UUID(as_uuid=True), nullable=False)
    commit_date = Column(DateTime, nullable=False)
    commit_date_tz_offset = Column(Integer, nullable=False)
    committer_contributor_name = Column(String, nullable=False)
    committer_contributor_key = Column(UUID(as_uuid=True), nullable=False)
    author_date = Column(DateTime, nullable=False)
    author_date_tz_offset = Column(Integer, nullable=False)
    author_contributor_key = Column(UUID(as_uuid=True),nullable=False)
    author_contributor_name = Column(String, nullable=False)
    commit_message = Column(Text, nullable=False)
    created_on_branch = Column(String, nullable=True)

    work_items = relationship('WorkItem',
                            secondary=work_items_commits,
                            back_populates="commits")

cached_commits = CachedCommit.__table__
UniqueConstraint(cached_commits.c.organization_key, cached_commits.c.repository_name, cached_commits.c.commit_key)


def recreate_all(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)