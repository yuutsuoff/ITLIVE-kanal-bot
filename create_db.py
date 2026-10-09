import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def create_db():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found in .env")
        return

    # Parse URL: postgresql+asyncpg://postgres:postgres@localhost:5432/itlive_hr
    # We need to connect to the default 'postgres' database to create 'itlive_hr'
    
    # Strip postgresql+asyncpg://
    base_url = db_url.replace("postgresql+asyncpg://", "postgres://")
    import urllib.parse
    parsed = urllib.parse.urlparse(base_url)
    
    user = parsed.username
    password = parsed.password
    host = parsed.hostname
    port = parsed.port
    target_db = parsed.path.lstrip('/')
    
    print(f"Connecting to postgres to ensure database '{target_db}' exists...")
    try:
        conn = await asyncpg.connect(user=user, password=password, host=host, port=port, database='postgres')
        # Check if db exists
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", target_db)
        if not exists:
            print(f"Creating database {target_db}...")
            await conn.execute(f'CREATE DATABASE "{target_db}"')
            print("Database created successfully!")
        else:
            print(f"Database {target_db} already exists.")
        await conn.close()
    except Exception as e:
        print(f"Failed to connect to postgres or create database: {e}")
        print("Make sure PostgreSQL is installed and running locally on port 5432 with user/password postgres/postgres")

if __name__ == "__main__":
    asyncio.run(create_db())
