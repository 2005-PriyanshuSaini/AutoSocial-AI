from sqlalchemy import Column, Integer, String, Text, Enum
from db import Base  # Make sure this points to the correct file
import enum

# Enum for status values
class StatusEnum(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)  # Removed index=True for performance
    status = Column(Enum(StatusEnum), default=StatusEnum.PENDING)
