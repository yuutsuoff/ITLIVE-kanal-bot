from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from bot.config import ADMIN_IDS
from bot.states.admin_states import AdminStates
from db.database import async_session
from sqlalchemy import select, func     
from db.models import Candidate, Evaluation, Question, Field
from db.crud import add_question_manual, delete_question, get_fields

router = Router()

def get_admin_kb():
    kb = [
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📝 Savollar")],
        [KeyboardButton(text="➕ Savol qo'shish"), KeyboardButton(text="🏠 Bosh menyu")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@router.message(Command("admin"))
@router.message(F.text == "🏠 Bosh menyu")
async def cmd_admin(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Siz admin emassiz! ❌")
        return
    
    await state.clear()
    async with async_session() as db:
        # Get stats
        total_result = await db.execute(select(func.count(Candidate.id)))
        total = total_result.scalar()
        
        # Get latest candidates
        cand_result = await db.execute(select(Candidate).order_by(Candidate.created_at.desc()).limit(5))
        candidates = cand_result.scalars().all()
        
        msg = "<b>👑 Admin Boshqaruv Paneli</b>\n\n"
        msg += f"📊 <b>Jami nomzodlar:</b> {total}\n\n"
        msg += "🕒 <b>Oxirgi 5 ta nomzod:</b>\n"
        
        for c in candidates:
            status_icon = "✅" if c.status == 'completed' else "⏳"
            username = f"(@{c.username})" if c.username else ""
            msg += f"{status_icon} {c.first_name} {c.last_name} {username}\n"
            
        import os
        public_url = os.getenv("PUBLIC_URL", os.getenv("RAILWAY_STATIC_URL", "http://localhost:8000"))
        if not public_url.startswith("http"):
            public_url = f"https://{public_url}"
            
        msg += f"\n🌐 Batafsil: {public_url}"
        await message.answer(msg, parse_mode="HTML", reply_markup=get_admin_kb())

@router.message(F.text == "📊 Statistika")
async def cmd_stats(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    
    async with async_session() as db:
        result = await db.execute(select(Evaluation))
        evals = result.scalars().all()
        
        if not evals:
            await message.answer("Hozircha tahlillar mavjud emas.")
            return
            
        avg_score = sum(e.overall_score for e in evals) / len(evals)
        await message.answer(f"📈 <b>O'rtacha ball:</b> {avg_score:.1f}\n✅ <b>Tahlil qilinganlar:</b> {len(evals)}", parse_mode="HTML")

# --- QUESTION CRUD ---

@router.message(F.text == "📝 Savollar")
async def list_questions(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    
    async with async_session() as db:
        result = await db.execute(select(Question).where(Question.is_active == True))
        questions = result.scalars().all()
        
        if not questions:
            await message.answer("Hozircha savollar yo'q.")
            return
            
        await message.answer("<b>📝 Savollar ro'yxati:</b>", parse_mode="HTML")
        for q in questions:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🗑 O'chirish", callback_query_data=f"del_q_{q.id}")]
            ])
            text = f"<b>Kategoriya:</b> {q.category}\n<b>Qiyinchilik:</b> {q.difficulty}\n<b>Savol:</b> {q.question_text}"
            await message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("del_q_"))
async def handle_delete_question(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    
    q_id = int(callback.data.split("_")[2])
    async with async_session() as db:
        await delete_question(db, q_id)
        await callback.answer("Savol o'chirildi! ✅")
        await callback.message.delete()

@router.message(F.text == "➕ Savol qo'shish")
async def start_add_question(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    
    await state.set_state(AdminStates.waiting_question_text)
    await message.answer("Yangi savol matnini kiriting:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True
    ))

@router.message(F.text == "❌ Bekor qilish")
async def cancel_admin(message: Message, state: FSMContext):
    await state.clear()
    await cmd_admin(message, state)

@router.message(AdminStates.waiting_question_text)
async def process_q_text(message: Message, state: FSMContext):
    await state.update_data(q_text=message.text)
    await state.set_state(AdminStates.waiting_question_category)
    
    async with async_session() as db:
        fields = await get_fields(db)
    
    kb = [[KeyboardButton(text=f.name)] for f in fields]
    kb.append([KeyboardButton(text="Logic"), KeyboardButton(text="Technical")])
    kb.append([KeyboardButton(text="❌ Bekor qilish")])
    
    await message.answer("Savol kategoriyasini tanlang yoki yozing:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@router.message(AdminStates.waiting_question_category)
async def process_q_cat(message: Message, state: FSMContext):
    await state.update_data(q_cat=message.text)
    await state.set_state(AdminStates.waiting_question_difficulty)
    
    kb = [
        [KeyboardButton(text="easy"), KeyboardButton(text="medium"), KeyboardButton(text="hard")],
        [KeyboardButton(text="❌ Bekor qilish")]
    ]
    await message.answer("Savol qiyinchiligini tanlang:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@router.message(AdminStates.waiting_question_difficulty)
async def process_q_diff(message: Message, state: FSMContext):
    data = await state.get_data()
    async with async_session() as db:
        await add_question_manual(
            db, 
            question_text=data['q_text'],
            category=data['q_cat'],
            difficulty=message.text
        )
    
    await message.answer("Savol muvaffaqiyatli qo'shildi! ✅")
    await state.clear()
    await cmd_admin(message, state)
