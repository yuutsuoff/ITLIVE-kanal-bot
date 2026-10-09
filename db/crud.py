from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import Candidate, Question, Answer, Evaluation, Admin, User, Field
from typing import List

async def create_candidate(db: AsyncSession, telegram_id: int, first_name: str, last_name: str, age: int, location: str, experience: str, hours_per_day: int, phone_number: str = None, field_id: int = None, username: str = None) -> Candidate:
    db_candidate = Candidate(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        age=age,
        location=location,
        experience=experience,
        field_id=field_id,
        hours_per_day=hours_per_day,
        phone_number=phone_number
    )
    db.add(db_candidate)
    await db.commit()
    await db.refresh(db_candidate)
    return db_candidate

async def get_fields(db: AsyncSession):
    result = await db.execute(select(Field).where(Field.is_active == True))
    return result.scalars().all()

async def create_field(db: AsyncSession, name: str) -> Field:
    db_field = Field(name=name)
    db.add(db_field)
    await db.commit()
    await db.refresh(db_field)
    return db_field

async def delete_field(db: AsyncSession, field_id: int):
    field = await db.get(Field, field_id)
    if field:
        field.is_active = False
        await db.commit()
    return field

async def get_user_by_username(db: AsyncSession, username: str) -> User:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()

async def create_user(db: AsyncSession, username: str, hashed_password: str) -> User:
    db_user = User(username=username, hashed_password=hashed_password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def get_candidate_by_telegram_id(db: AsyncSession, telegram_id: int) -> Candidate:
    result = await db.execute(select(Candidate).where(Candidate.telegram_id == telegram_id))
    return result.scalars().first()

async def get_active_questions(db: AsyncSession) -> List[Question]:
    result = await db.execute(select(Question).where(Question.is_active == True))
    return result.scalars().all()

async def create_answer(db: AsyncSession, candidate_id: int, question_id: int, answer_text: str) -> Answer:
    db_answer = Answer(
        candidate_id=candidate_id,
        question_id=question_id,
        answer_text=answer_text
    )
    db.add(db_answer)
    await db.commit()
    await db.refresh(db_answer)
    return db_answer

async def update_candidate_status(db: AsyncSession, candidate_id: int, status: str):
    candidate = await db.get(Candidate, candidate_id)
    if candidate:
        candidate.status = status
        await db.commit()
        await db.refresh(candidate)
    return candidate

async def create_question(db: AsyncSession, question_text: str, category: str = "dynamic", difficulty: str = "medium") -> Question:
    db_question = Question(
        question_text=question_text,
        category=category,
        difficulty=difficulty,
        is_active=False  # Dynamic questions are not active for everyone
    )
    db.add(db_question)
    await db.commit()
    await db.refresh(db_question)
    return db_question

async def get_candidate_answers(db: AsyncSession, candidate_id: int) -> List[Answer]:
    result = await db.execute(select(Answer).where(Answer.candidate_id == candidate_id))
    return result.scalars().all()

async def create_evaluation(db: AsyncSession, eval_data: dict) -> Evaluation:
    db_eval = Evaluation(**eval_data)
    db.add(db_eval)
    await db.commit()
    await db.refresh(db_eval)
    return db_eval

async def get_admins(db: AsyncSession) -> List[Admin]:
    result = await db.execute(select(Admin))
    return result.scalars().all()

async def delete_question(db: AsyncSession, question_id: int):
    question = await db.get(Question, question_id)
    if question:
        await db.delete(question)
        await db.commit()
    return question

async def add_question_manual(db: AsyncSession, question_text: str, category: str, difficulty: str) -> Question:
    db_question = Question(
        question_text=question_text,
        category=category,
        difficulty=difficulty,
        is_active=True
    )
    db.add(db_question)
    await db.commit()
    await db.refresh(db_question)
    return db_question
