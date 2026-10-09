from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

from db.database import get_db
from db.models import Candidate, Evaluation, Answer, User, Field
from db.crud import get_user_by_username, get_fields, create_field, delete_field
from io import BytesIO
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from datetime import datetime, timedelta
import asyncio
from contextlib import asynccontextmanager
from aiogram import Bot, Dispatcher
from bot.config import BOT_TOKEN
from bot.handlers import start, registration, questions, admin
from db.database import init_db
from seed import seed
from seed_admin import seed_admin

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    bot_ref = {}
    
    async def start_services():
        # 1. Database tables & seeds
        try:
            await init_db()
            await seed()
            await seed_admin()
        except Exception as e:
            print(f"Database init in lifespan: {e}")
            
        # 2. Telegram Bot Polling
        if BOT_TOKEN:
            try:
                bot = Bot(token=BOT_TOKEN)
                bot_ref["bot"] = bot
                dp = Dispatcher()
                dp.include_router(admin.router)
                dp.include_router(start.router)
                dp.include_router(registration.router)
                dp.include_router(questions.router)
                
                await bot.delete_webhook(drop_pending_updates=True)
                print("Telegram Bot polling started successfully alongside FastAPI!")
                await dp.start_polling(bot)
            except Exception as e:
                print(f"Failed to start bot in lifespan: {e}")
        else:
            print("BOT_TOKEN is not set; bot not started.")

    bg_task = asyncio.create_task(start_services())
    
    # Yield immediately so Uvicorn binds port instantly and Render detects it!
    yield
    
    bg_task.cancel()
    if "bot" in bot_ref:
        try:
            await bot_ref["bot"].session.close()
        except Exception:
            pass


app = FastAPI(title="ITLIVE HR Admin API", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("API_SECRET_KEY", "very-secret-key"))

templates = Jinja2Templates(directory="api/templates")

app.mount("/static", StaticFiles(directory="api/templates"), name="static")

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

# Helper to check auth
async def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        return None
    return user

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    print(f"Login attempt for username: {username}")
    user = await get_user_by_username(db, username)
    if not user:
        print(f"User {username} not found in database")
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Login yoki parol noto'g'ri"})
    
    is_valid = pwd_context.verify(password, user.hashed_password)
    print(f"Password valid for {username}: {is_valid}")
    
    if not is_valid:
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Login yoki parol noto'g'ri"})
    
    request.session["user"] = username
    return RedirectResponse(url="/", status_code=303)


@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/login", status_code=303)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db), user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    candidates_result = await db.execute(
        select(Candidate).options(selectinload(Candidate.evaluation))
    )
    candidates = candidates_result.scalars().all()
    
    total = len(candidates)
    hired = sum(1 for c in candidates if c.evaluation and c.evaluation.recommendation == 'hire')
    rejected = sum(1 for c in candidates if c.evaluation and c.evaluation.recommendation == 'reject')
    
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "total": total,
        "hired": hired,
        "rejected": rejected,
        "user": user
    })

@app.get("/candidates", response_class=HTMLResponse)
async def candidates_list(request: Request, start_date: str = None, end_date: str = None, db: AsyncSession = Depends(get_db), user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    query = select(Candidate).options(selectinload(Candidate.evaluation), selectinload(Candidate.field)).order_by(Candidate.created_at.desc())
    
    if start_date:
        query = query.where(Candidate.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        # End date should include the whole day
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        query = query.where(Candidate.created_at < end_dt)
        
    result = await db.execute(query)
    candidates = result.scalars().all()
    
    return templates.TemplateResponse(request=request, name="candidates.html", context={
        "candidates": candidates,
        "user": user,
        "start_date": start_date,
        "end_date": end_date
    })

@app.post("/candidates/{candidate_id}/status")
async def update_status(candidate_id: int, status: str = Form(...), db: AsyncSession = Depends(get_db), user: str = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401)
        
    candidate = await db.get(Candidate, candidate_id)
    if candidate:
        candidate.status = status
        await db.commit()
    return RedirectResponse(url=f"/candidates/{candidate_id}", status_code=303)

@app.get("/fields", response_class=HTMLResponse)
async def fields_list(request: Request, db: AsyncSession = Depends(get_db), user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    fields = await get_fields(db)
    return templates.TemplateResponse(request=request, name="fields.html", context={"fields": fields, "user": user})


@app.post("/fields")
async def add_field(name: str = Form(...), db: AsyncSession = Depends(get_db), user: str = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401)
    await create_field(db, name)
    return RedirectResponse(url="/fields", status_code=303)

@app.post("/fields/{field_id}/delete")
async def remove_field(field_id: int, db: AsyncSession = Depends(get_db), user: str = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401)
    await delete_field(db, field_id)
    return RedirectResponse(url="/fields", status_code=303)

@app.get("/export")
async def export_excel(db: AsyncSession = Depends(get_db), user: str = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401)
        
    result = await db.execute(
        select(Candidate).options(selectinload(Candidate.evaluation), selectinload(Candidate.field))
    )
    candidates = result.scalars().all()
    
    data = []
    for c in candidates:
        data.append({
            "ID": c.id,
            "F.I.SH": f"{c.first_name} {c.last_name}",
            "Telefon": c.phone_number,
            "Soha": c.field.name if c.field else "Noma'lum",
            "Manzil": c.location,
            "Yosh": c.age,
            "Tajriba": c.experience,
            "Ish vaqti": c.hours_per_day,
            "Status": c.status,
            "Ball": c.evaluation.overall_score if c.evaluation else "N/A",
            "Tavsiya": c.evaluation.recommendation if c.evaluation else "N/A",
            "Sana": c.created_at.strftime("%Y-%m-%d %H:%M")
        })
        
    import pandas as pd
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Candidates')
    
    output.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename="candidates_report.xlsx"'
    }
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.get("/candidates/{candidate_id}", response_class=HTMLResponse)
async def candidate_detail(request: Request, candidate_id: int, db: AsyncSession = Depends(get_db), user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    result = await db.execute(
        select(Candidate)
        .options(
            selectinload(Candidate.field),
            selectinload(Candidate.evaluation), 
            selectinload(Candidate.answers).selectinload(Answer.question)
        )
        .where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Nomzod topilmadi")
        
    return templates.TemplateResponse(request=request, name="candidate_detail.html", context={
        "candidate": candidate,
        "user": user
    })

