import asyncio
from db.database import async_session
from db.crud import create_user, get_user_by_username
from passlib.context import CryptContext
from sqlalchemy import update
from db.models import User

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

async def seed_admin():
    username = "admin"
    password = "admin123"
    
    async with async_session() as db:
        existing = await get_user_by_username(db, username)
        hashed_password = pwd_context.hash(password)
        
        if existing:
            print(f"User {username} already exists. Updating password...")
            existing.hashed_password = hashed_password
            await db.commit()
            print("Password updated successfully.")
        else:
            await create_user(db, username, hashed_password)
            print(f"Admin user created: {username} / {password}")

if __name__ == "__main__":
    asyncio.run(seed_admin())
