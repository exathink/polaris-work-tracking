# -*- coding: utf-8 -*-

# Copyright: © Exathink, LLC (2011-2018) All Rights Reserved

# Unauthorized use or copying of this file and its contents, via any medium
# is strictly prohibited. The work product in this file is proprietary and
# confidential.

# Author: Krishna Kumar


import logging
from datetime import datetime

logger = logging.getLogger('polaris.work_tracking.db.model')

from sqlalchemy import \
    Index, Column, BigInteger, Integer, String, Text, DateTime, \
    Boolean, MetaData, ForeignKey, and_, UniqueConstraint, cast, text

from polaris.utils.config import get_config_provider
from polaris.utils.collections import dict_merge
from polaris.common.enums import WorkItemsSourceImportState
from sqlalchemy.orm import relationship, object_session
from sqlalchemy.sql import select, func

from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from polaris.common import db

Base = db.polaris_declarative_base(metadata=MetaData(schema='work_tracking'))

config = get_config_provider()


class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True)
    key = Column(UUID(as_uuid=True), nullable=False, unique=True)
    name = Column(String, nullable=False)

    account_key = Column(UUID(as_uuid=True), nullable=False)
    organization_key = Column(UUID(as_uuid=True), nullable=False)

    work_items_sources = relationship('WorkItemsSource')

    @classmethod
    def find_by_key(cls, session, project_key):
        return session.query(cls).filter(cls.key == project_key).first()


projects = Project.__table__


class WorkItemsSource(Base):
    __tablename__ = 'work_items_sources'

    id = Column(Integer, primary_key=True)
    key = Column(UUID(as_uuid=True), nullable=False, unique=True)
    connector_key = Column(UUID(as_uuid=True), nullable=False, server_default=text('uuid_generate_v4()'))

    # type of integration: github, github_enterprise, jira, pivotal_tracker etc..
    integration_type = Column(String, nullable=False)

    # integration specific sub type: for example github_repository_issues, github_organization_issues
    # this type determines the shape of the expected parameters for an instance of the WorkItemsSource
    work_items_source_type = Column(String(128), nullable=False)
    # stores provider specific attributes for the work_items_source_type if needed.
    parameters = Column(JSONB, nullable=True, default={}, server_default='{}')
    # Custom fields specific to work item source
    custom_fields = Column(JSONB, nullable=True, default=[], server_default='[]')

    # App facing attributes.
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    # An instance can be tied to an account and an organization
    account_key = Column(UUID(as_uuid=True), nullable=True)
    organization_key = Column(UUID(as_uuid=True), nullable=True)

    # Commit Mapping: governs which repositories will have their commits mapped
    # to work_items in this work_item_source.
    # Commit mapping scope specifies the repositories that are mapped to this
    # work item source. The valid values are ('organization', 'project', 'repository')
    # Given the commit mapping scope key, commits originating from all repositories
    # within that specific scope (instance of org, project or repository) will be evaluated to
    # see if they can be mapped to a given work item originating from this work items source.
    commit_mapping_scope = Column(String, nullable=False, default='organization', server_default="'organization'")
    # given the scope, the key determines which specific instance of that scope will be searched.
    # this may be nullable, but needs to be non null on creation before commit mapping can proceed.
    commit_mapping_scope_key = Column(UUID(as_uuid=True), nullable=True)

    # This is text prefix that can be used to map commits from the work items source using the
    # display_id. For Jira this is the project key PP in the PP-51 display id for example.
    # Not useful for providers where the display id is a number, but when there is a text prefix
    # we can use this find out potential matches between commits and work items, missing matches etc.
    # so this is a useful field to capture if we have it.
    commit_mapping_prefix = Column(String, nullable=True)

    # Sync Status: the last point at which work items from this source were synced with the source system.
    last_synced = Column(DateTime, nullable=True)

    # Source data
    # The unique id of this work_items_source in the source system.
    # we expect this to be unique within the given connector id but wont enforce it
    # as a DB constraint until we understand a few more integrations a bit better.
    # we are leaving this nullable until we migrate github.
    source_id = Column(String, nullable=True, index=True)
    source_created_at = Column(DateTime, nullable=True)
    source_updated_at = Column(DateTime, nullable=True)
    # Stores webhook details or any other info related to source
    source_data = Column(JSONB, nullable=False, default={}, server_default='{}')
    # List of states available in work items source
    source_states = Column(JSONB, nullable=True, default=[], server_default='[]')
    # Import: Legal values from WorkItemsSourceImportState enum
    import_state = Column(String, nullable=False, server_default=WorkItemsSourceImportState.disabled.value)

    # Relationships
    work_items = relationship('WorkItem')
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=True)
    project = relationship('Project', back_populates='work_items_sources')

    @classmethod
    def find_by_organization_key(cls, session, organization_key):
        return session.query(cls).filter(cls.organization_key == organization_key).all()

    @classmethod
    def find_by_key(cls, session, work_items_source_key):
        return session.query(cls).filter(cls.key == work_items_source_key).first()

    @classmethod
    def find_by_connector_key_and_source_id(cls, session, connector_key, source_id):
        return session.query(cls).filter(
            and_(
                cls.connector_key == connector_key,
                cls.source_id == source_id
            )
        ).first()

    @classmethod
    def find_by_integration_type_and_parameters(cls, session, integration_type, **parameters):
        return session.query(cls).filter(
            and_(
                cls.integration_type == integration_type,
                *[
                    cls.parameters[k] == cast(parameters[k], JSONB)
                    for k in parameters
                ]
            )
        ).all()

    """
        Fetches work items for the given work items source in batches. 

        You can use this to page through the work items by passing in the batch size 
        and the starting work item id.

        :param work_items_source_key: Key of the work items source
        :param batch_size: Size of the batch
        :param starting: Starting work item id
        :param join_this: Session to join
        :return: A tuple (Batch of work items, next starting work item id)
    """
    @classmethod
    def fetch_work_items_batch(cls, work_items_source_key, batch_size=1000, starting=None, join_this=None):
        with db.orm_session(join_this) as session:
            work_items_source = cls.find_by_key(session, work_items_source_key)
            return db.result_batch(
                session.query(WorkItem).filter(WorkItem.work_items_source_id == work_items_source.id),
                WorkItem.id,
                batch_size=batch_size,
                starting=starting,
                desc=True
            )

    @classmethod
    def populate_required_values(self, work_item_source):
        required_values_with_defaults = dict(
            commit_mapping_scope='organization',
            source_data={},
            source_states=[],  # source states is though nullable, set the default
        )
        for key, value in required_values_with_defaults.items():
            if key not in work_item_source.keys():
                work_item_source[key] = value
        return work_item_source

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

    @property
    def most_recently_updated_work_item_source_id(self):
        return object_session(self).scalar(
            select(
                [work_items.c.source_id]
            ).where(
                and_(
                    work_items.c.source_last_updated ==
                    select(
                        [func.max(work_items.c.source_last_updated)]
                    ).where(
                        work_items.c.work_items_source_id == self.id
                    ).alias(),
                    work_items.c.work_items_source_id == self.id
                )
            )
        )

    def get_summary_info(self):
        return dict(
            work_items_source_key=self.key,
            name=self.name,
            integration_type=self.integration_type,
            commit_mapping_scope=self.commit_mapping_scope,
            commit_mapping_scope_key=self.commit_mapping_scope_key
        )

    def find_work_items_by_source_id(self, session, source_ids):
        return session.query(WorkItem).filter(
            and_(
                work_items.c.work_items_source_id == self.id,
                work_items.c.source_id.in_(source_ids)
            )
        )

    def should_sync(self, sync_interval=int(config.get('work_items_sources_min_secs_between_syncs', 30))):
        return self.last_synced is None or (datetime.utcnow() - self.last_synced).total_seconds() > sync_interval

    def set_synced(self):
        self.last_synced = datetime.utcnow()

    def update(self, work_items_source_data):
        updatable_fields = [
            'parameters',
            'custom_fields',
            'name',
            'description',
            'url',
            'commit_mapping_scope',
            'commit_mapping_scope_key',
            'last_synced',
            'source_updated_at',
            'source_data',
            'source_states',
            'import_state'
        ]
        updated = []
        for attribute, value in work_items_source_data.items():
            if attribute in updatable_fields:
                if getattr(self, attribute) != value:
                    if attribute == 'source_data':
                        self.update_source_data(value)
                    else:
                        setattr(self, attribute, value)
                else:
                    logger.info(f"Attribute value unchanged for attribute: {attribute}")
                updated.append(True)
            else:
                logger.info(f"Cannot update attribute : {attribute}")
                updated.append(False)
        return all(updated)

    def update_source_data(self, source_data):
        # JSON-dict field is by default immutable in sqlalchemy. So updating self.source_data directly does not work. \
        # We need to copy to new dict and overwrite the whole jsonb dict with the new dict.
        new_source_data = dict(self.source_data)
        for key, value in source_data.items():
            new_source_data[key] = value
        self.source_data = new_source_data

    def update_parameters(self, work_items_source_parameters):
        self.parameters = dict_merge(
            dict(self.parameters),
            work_items_source_parameters
        )




work_items_sources = WorkItemsSource.__table__
UniqueConstraint(work_items_sources.c.connector_key, work_items_sources.c.source_id)


class WorkItem(Base):
    __tablename__ = 'work_items'

    id = Column(BigInteger, primary_key=True)
    key = Column(UUID(as_uuid=True), nullable=False, unique=True)

    # ID of the item in the source system, used to cross ref this instance for updates etc.
    source_id = Column(String, nullable=True)

    # These are provider specific types: values for each provider are drawn from enums in polaris.common.enum
    # The work_items_source implementation for the type maps these enums from the source system. These types
    # are displayed in the UI and meaningful to the application. Eg: Include Bug, Story, Issue, PullRequests etc.
    work_item_type = Column(String, nullable=False)

    # App fields. These are relevant to the app and checked for updates.
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    is_bug = Column(Boolean, nullable=False, default=False, server_default='FALSE')
    tags = Column(ARRAY(String), nullable=False, default=[], server_default='{}')
    url = Column(String, nullable=True)
    source_state = Column(String, nullable=False)
    source_display_id = Column(String, nullable=False)
    priority = Column(String, nullable=True)
    releases = Column(ARRAY(String), nullable=True, default=[], server_default='{}')
    story_points = Column(Integer, nullable=True)
    sprints = Column(ARRAY(String), nullable=True, default=[], server_default='{}')
    flagged = Column(Boolean, nullable=True, default=False, server_default='FALSE')
    changelog = Column(JSONB, nullable=True)

    # timestamps for synchronization
    source_created_at = Column(DateTime, nullable=False)
    source_last_updated = Column(DateTime, nullable=True)
    last_sync = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    # Information related to Epic
    is_epic = Column(Boolean, nullable=False, default=False, server_default='FALSE')
    parent_source_display_id = Column(String, nullable=True)
    parent_id = Column(Integer, ForeignKey('work_items.id'), nullable=True)
    parent = relationship('WorkItem', remote_side='WorkItem.id')

    # Fields to be used to match commits
    commit_identifiers = Column(JSONB, nullable=True, default=[], server_default='[]')

    # Field to identify if the work item is moved from current work items source
    is_moved_from_current_source = Column(Boolean, nullable=True, default=False, server_default='FALSE')

    # Work Items Source relationship
    work_items_source_id = Column(Integer, ForeignKey('work_items_sources.id'))
    work_items_source = relationship('WorkItemsSource', back_populates='work_items')

    # Work Item Source Payload from API
    api_payload = Column(JSONB, nullable=True, default={}, server_default='{}')

    @classmethod
    def find_by_id(cls, session, id):
        return session.query(cls).filter(
            cls.id == id
        ).first()

    @classmethod
    def find_by_key(cls, session, key):
        return session.query(cls).filter(
            cls.key == key
        ).first()

    @classmethod
    def find_by_source_display_id(cls, session, work_items_source_id, source_display_id):
        return session.query(cls).filter(and_(
            cls.work_items_source_id == work_items_source_id,
            cls.source_display_id == source_display_id
        )).first()

    @classmethod
    def find_by_work_item_source_key_source_id(cls, session, work_items_source_key, source_id):
        return session.query(cls).filter(
            and_(
                cls.work_items_source.key == work_items_source_key,
                cls.source_id == source_id
            )
        ).first()

    @classmethod
    def find_by_work_item_source_id_source_id(cls, session, work_items_source_id, source_id):
        return session.query(cls).filter(
            and_(
                cls.work_items_source_id == work_items_source_id,
                cls.source_id == source_id
            )
        ).first()

    # This method will return true only if the specified attributes have changed.
    # remaining attributes may be updated, but they are "internal" updates and the changes
    # are not material to the rest of the app. So the result value should be used
    # to decide whether or not to propagate the update to the rest of the system.
    def update(self, work_item_data):
        updated = False
        for attribute in ['name', 'description', 'is_bug', 'work_item_type', 'is_epic', 'tags', 'url', 'source_state',
                          'source_display_id', 'parent_id', 'api_payload', 'work_items_source_id', 'commit_identifiers',
                          'parent_source_display_id','priority','releases','story_points','sprints','flagged','changelog']:
            if work_item_data.get(attribute) is not None and getattr(self, attribute) != work_item_data.get(attribute):
                setattr(self, attribute, work_item_data.get(attribute))
                updated = True

        self.last_sync = datetime.utcnow()
        self.source_last_updated = work_item_data.get('source_last_updated')
        return updated


work_items = WorkItem.__table__
Index('ix_work_items_work_item_source_id_source_display_id', work_items.c.work_items_source_id,
      work_items.c.source_display_id)
UniqueConstraint(work_items.c.work_items_source_id, work_items.c.source_id)


def recreate_all(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


