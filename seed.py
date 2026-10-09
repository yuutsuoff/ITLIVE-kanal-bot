import asyncio
from db.database import async_session
from db.models import Question, Field
from sqlalchemy import select

async def seed():
    async with async_session() as db:
        # Check if questions already exist
        result = await db.execute(select(Question))
        if result.scalars().first():
            print("Questions already seeded.")
        else:
            print("Seeding initial questions...")
            questions = [
                Question(
                    category="Logic", difficulty="easy",
                    question_text="Agar haftada 3 marta sport qilsangiz va har safar 45 daqiqa, bir oyda necha daqiqa sport qilasiz? (4 haftani hisoblang)"
                ),
                Question(
                    category="Logic", difficulty="medium",
                    question_text="Siz katta loyihani boshqarmoqdasiz. Muddati ertaga, lekin jamoadagi 2 kishi kasal. Qanday harakat qilasiz?"
                ),
                Question(
                    category="Technical", difficulty="easy",
                    question_text="Git nima? Nima uchun ishlatiladi?"
                ),
                Question(
                    category="Technical", difficulty="medium",
                    question_text="API nima? Tushuntirib bering."
                )
            ]
            db.add_all(questions)
            await db.commit()
            print("Successfully seeded questions.")

        # Seed Fields
        result = await db.execute(select(Field))
        if not result.scalars().first():
            print("Seeding initial fields...")
            fields = [
                Field(name="HR"),
                Field(name="Call Operator"),
                Field(name="Mentor"),
                Field(name="Admin"),
                Field(name="Assistant")
            ]
            db.add_all(fields)
            await db.commit()
            print("Successfully seeded fields.")
        else:
            print("Fields already seeded.")

if __name__ == "__main__":
    asyncio.run(seed())
