import subprocess
import os
import sys
import time
import asyncio

async def ensure_db_initialized():
    try:
        from db.database import init_db
        from seed import seed
        from seed_admin import seed_admin
        print("Initializing database tables...")
        await init_db()
        print("Seeding initial questions and fields...")
        await seed()
        print("Ensuring admin user...")
        await seed_admin()
        print("Database ready!")
    except Exception as e:
        print(f"Database initialization notice: {e}")

def start_api():
    port = os.getenv("PORT", "8000")
    print(f"Starting FastAPI Web Dashboard on port {port}...")
    env = os.environ.copy()
    env["PYTHONPATH"] = f".:{env.get('PYTHONPATH', '')}"
    
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", port],
        env=env
    )

def start_bot():
    print("Starting Telegram Bot...")
    env = os.environ.copy()
    env["PYTHONPATH"] = f".:{env.get('PYTHONPATH', '')}"
    
    return subprocess.Popen(
        [sys.executable, "-m", "bot.main"],
        env=env
    )

if __name__ == "__main__":
    print("--- Starting Render Deployment ---")
    asyncio.run(ensure_db_initialized())
    
    api_proc = start_api()
    bot_proc = start_bot()
    
    print(f"API PID: {api_proc.pid}")
    print(f"Bot PID: {bot_proc.pid}")
    print("Monitoring services...")
    
    try:
        while True:
            time.sleep(10)
            if api_proc.poll() is not None:
                print("API process exited unexpectedly.")
                bot_proc.terminate()
                sys.exit(1)
            if bot_proc.poll() is not None:
                print("Bot process exited unexpectedly.")
                api_proc.terminate()
                sys.exit(1)
    except KeyboardInterrupt:
        print("Stopping services...")
        api_proc.terminate()
        bot_proc.terminate()
