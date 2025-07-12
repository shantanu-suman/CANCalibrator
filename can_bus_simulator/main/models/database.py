#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

import logging
logger = logging.getLogger(__name__)

# Import configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import config

# Create database engine
engine = create_engine(config.DATABASE_URI)

# Create session factory
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))

# Base class for all models
Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    """
    Initialize the database, creating all tables if they don't exist.
    
    Import all models here to ensure they are registered with SQLAlchemy.
    """
    import main.models.vehicle
    import main.models.can_message
    import main.models.label

    # Create tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Error creating database tables: %s", str(e))

def reset_db():
    """
    Reset the database by dropping all tables and recreating them.
    WARNING: This will delete all data!
    """
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped")
        init_db()
        logger.info("Database reset complete")
    except Exception as e:
        logger.error("Error resetting database: %s", str(e))