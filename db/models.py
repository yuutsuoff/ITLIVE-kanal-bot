from sqlalchemy import Column, Integer, String, Float, Text, Boolean, BigInteger, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    location = Column(String(200), nullable=False)
    experience = Column(Text, nullable=True)
    phone_number = Column(String(20), nullable=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=True)
    hours_per_day = Column(Integer, nullable=False)
    status = Column(String(20), default='in_progress')
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    field = relationship("Field", back_populates="candidates")
    answers = relationship("Answer", back_populates="candidate", cascade="all, delete")
    evaluation = relationship("Evaluation", back_populates="candidate", uselist=False, cascade="all, delete")

class Field(Base):
    __tablename__ = "fields"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)

    candidates = relationship("Candidate", back_populates="field")

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False)
    difficulty = Column(String(20), nullable=False)
    question_text = Column(Text, nullable=False)
    expected_topics = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)

    answers = relationship("Answer", back_populates="question")

class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    answer_text = Column(Text, nullable=False)
    answered_at = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("Answer" if False else Candidate, back_populates="answers")
    question = relationship("Question", back_populates="answers")

class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), unique=True)
    overall_score = Column(Float, nullable=False)
    logic_score = Column(Float, nullable=True)
    technical_score = Column(Float, nullable=True)
    clarity_score = Column(Float, nullable=True)
    strengths = Column(JSON, nullable=True)
    weaknesses = Column(JSON, nullable=True)
    recommendation = Column(String(20), nullable=False)
    ai_summary = Column(Text, nullable=True)
    evaluated_at = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="evaluation")

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100), nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
