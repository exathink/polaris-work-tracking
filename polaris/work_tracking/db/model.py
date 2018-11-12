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
    Table, Column, BigInteger, Integer, String, Text, DateTime, \
    Boolean, MetaData, ForeignKey, TIMESTAMP, and_

from sqlalchemy.orm import relationship, object_session
from sqlalchemy.sql import cast

from sqlalchemy.dialects.postgresql import UUID, JSONB

from polaris.common import db

Base = db.polaris_declarative_base(metadata=MetaData(schema='work_tracking'))

class WorkItem(Base):
    __tablename__ = 'work_items'

    id = Column(BigInteger, primary_key=True)
    key = Column(UUID(as_uuid=True), nullable=False, unique=True)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    is_bug = Column(Boolean, nullable=False, default=False, server_default='FALSE')

