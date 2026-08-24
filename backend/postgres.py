from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import config

dbengine= create_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=dbengine)

if not dbengine:
    raise RuntimeError("Failed to connect to postgres")

#Get a database session for each request, and the close it after the request is done.
def get_database():
    db_session= SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()

