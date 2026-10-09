import subprocess
import os
import sys
import time

def run_migrations():
    print("--- Environment Info ---")
    print(f"CWD: {os.getcwd()}")
    print(f"PYTHONPATH: {os.getenv('PYTHONPATH')}")
    print(f"Files in root: {os.listdir('.')}")
    
    # Ensure current directory is in PYTHONPATH for the subprocesses
    env = os.environ.copy()
    env["PYTHONPATH"] = f".:{env.get('PYTHONPATH', '')}"
    
    print("Running migrations...")
    try:
        # Use -m alembic to ensure it finds the config
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"], 
            env=env,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"Migration failed with code {result.returncode}")
            print(f"Error: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"Migration error: {e}")
        return False

def run_seeding():
    env = os.environ.copy()
    env["PYTHONPATH"] = f".:{env.get('PYTHONPATH', '')}"
    
    print("Seeding database (fields and questions)...")
    try:
        subprocess.run([sys.executable, "seed.py"], env=env)
    except Exception as e:
        print(f"Seeding error (seed.py): {e}")
        
    print("Seeding admin user...")
    try:
        subprocess.run([sys.executable, "seed_admin.py"], env=env)
    except Exception as e:
        print(f"Seeding error (seed_admin.py): {e}")

def start_api():
    port = os.getenv("PORT", "8080")
    print(f"Starting API on port {port}...")
    env = os.environ.copy()
    env["PYTHONPATH"] = f".:{env.get('PYTHONPATH', '')}"
    
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", port],
        env=env
    )

def start_bot():
    print("Starting Bot...")
    env = os.environ.copy()
    env["PYTHONPATH"] = f".:{env.get('PYTHONPATH', '')}"
    
    return subprocess.Popen(
        [sys.executable, "-m", "bot.main"],
        env=env
    )

if __name__ == "__main__":
    # Wait for DB to be ready
    print("Waiting for database to initialize (5s)...")
    time.sleep(5)
    
    if run_migrations():
        run_seeding()
    else:
        print("CRITICAL: Migrations failed. Attempting to start anyway...")
    
    api_proc = start_api()
    bot_proc = start_bot()
    
    print("--- Processes started ---")
    print(f"API PID: {api_proc.pid}")
    print(f"Bot PID: {bot_proc.pid}")
    print("Monitoring...")
    
    try:
        while True:
            time.sleep(10)
            if api_proc.poll() is not None:
                print("API process terminated unexpectedly.")
                bot_proc.terminate()
                sys.exit(1)
            if bot_proc.poll() is not None:
                print("Bot process terminated unexpectedly.")
                api_proc.terminate()
                sys.exit(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        api_proc.terminate()
        bot_proc.terminate()
