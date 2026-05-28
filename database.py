from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DB_URL = "sqlite:///golfbot.db"

# connect_args={"check_same_thread": False} is required for SQLite under multi-threaded contexts
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# SQLAlchemy ORM Model
class BrokenBall(Base):
    __tablename__ = "broken_balls"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String, nullable=False)
    location = Column(String, nullable=False)
    image = Column(String, nullable=True)

def init_db():
    """데이터베이스 및 테이블 스키마 생성"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """FastAPI Depends용 DB 세션 Generator"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
