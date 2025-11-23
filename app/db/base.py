"""
Database Base

Base configuration for SQLAlchemy:
- Declarative base
- Naming conventions
- Metadata
"""

from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declarative_base

# Naming convention for constraints
# This ensures consistent constraint names across databases
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)

# Declarative base
Base = declarative_base(metadata=metadata)