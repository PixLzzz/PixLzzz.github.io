"""SQLAlchemy models."""
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from database import Base


class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500))
    price = Column(Float, nullable=False)
    address = Column(String(500))
    neighborhood = Column(String(200))
    bedrooms = Column(Integer)
    bathrooms = Column(Integer)
    area_sqft = Column(Float)
    source = Column(String(50), index=True)  # centris | duproprio | remax
    url = Column(String(1000), unique=True, nullable=False, index=True)
    image_url = Column(String(1000))
    description = Column(Text)
    has_terrace = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
