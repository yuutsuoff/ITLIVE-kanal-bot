from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from bot.states.candidate_states import CandidateStates

router = Router()

@router.message(F.text == "Ha ✅")
async def start_registration(message: Message, state: FSMContext):
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile
    import os
    
    video_path = os.path.join("vid", "doc_2026-05-06_17-08-46.mp4")
    if os.path.exists(video_path):
        try:
            await message.answer_video_note(FSInputFile(video_path))
        except Exception as e:
            print(f"Error sending video note: {e}")

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Kontaktni yuborish 📱", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await state.set_state(CandidateStates.waiting_contact)
    await message.answer("Ajoyib! Ro'yxatdan o'tishni boshlash uchun telefon raqamingizni yuboring:", reply_markup=kb)

@router.message(CandidateStates.waiting_contact)
async def process_contact(message: Message, state: FSMContext):
    if not message.contact:
        await message.answer("Iltimos, pastdagi tugmani bosib telefon raqamingizni yuboring.")
        return
        
    await state.update_data(phone_number=message.contact.phone_number)
    await state.set_state(CandidateStates.waiting_first_name)
    from aiogram.types import ReplyKeyboardRemove
    await message.answer("Rahmat! Endi ismingizni kiriting:", reply_markup=ReplyKeyboardRemove())

@router.message(F.text == "Yo'q ❌")
async def cancel_registration(message: Message, state: FSMContext):
    await state.clear()
    from aiogram.types import ReplyKeyboardRemove
    await message.answer("Tushunarli. Agar fikringiz o'zgarsa, /start tugmasini bosing.", reply_markup=ReplyKeyboardRemove())

@router.message(CandidateStates.waiting_first_name)
async def process_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await state.set_state(CandidateStates.waiting_last_name)
    await message.answer("Familiyangizni kiriting:")

@router.message(CandidateStates.waiting_last_name)
async def process_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    await state.set_state(CandidateStates.waiting_age)
    await message.answer("Yoshingizni kiriting (raqam ko'rinishida):")

@router.message(CandidateStates.waiting_age)
async def process_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, yoshingizni raqamda kiriting.")
        return
    age = int(message.text)
    if age < 16 or age > 60:
        await message.answer("Yoshingiz 16 va 60 orasida bo'lishi kerak. Qayta kiriting:")
        return
    await state.update_data(age=age)
    await state.set_state(CandidateStates.waiting_location)
    await message.answer("Qaysi shahar/tumandansiz?")

@router.message(CandidateStates.waiting_location)
async def process_location(message: Message, state: FSMContext):
    await state.update_data(location=message.text)
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Bor"), KeyboardButton(text="Yo'q")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await state.set_state(CandidateStates.waiting_experience)
    await message.answer("Ish tajribangiz bormi?", reply_markup=kb)

@router.message(CandidateStates.waiting_experience)
async def process_experience(message: Message, state: FSMContext):
    if message.text.lower() == "bor":
        await state.set_state(CandidateStates.waiting_exp_detail)
        from aiogram.types import ReplyKeyboardRemove
        await message.answer("Qancha va qanday tajribangiz bor? Qisqacha yozing.", reply_markup=ReplyKeyboardRemove())
    else:
        await state.update_data(experience="Yo'q")
        await state.set_state(CandidateStates.waiting_hours)
        from aiogram.types import ReplyKeyboardRemove
        await message.answer("Kuniga necha soat ishlashingiz mumkin? (raqam kiriting)", reply_markup=ReplyKeyboardRemove())

@router.message(CandidateStates.waiting_exp_detail)
async def process_exp_detail(message: Message, state: FSMContext):
    await state.update_data(experience=message.text)
    await state.set_state(CandidateStates.waiting_hours)
    await message.answer("Kuniga necha soat ishlashingiz mumkin? (raqam kiriting)")

@router.message(CandidateStates.waiting_hours)
async def process_hours(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, soatni raqamda kiriting.")
        return
    hours = int(message.text)
    if hours < 1 or hours > 16:
        await message.answer("Iltimos, 1 dan 16 gacha bo'lgan raqam kiriting.")
        return
    
    await state.update_data(hours=hours)
    
    from db.database import async_session
    from db.crud import get_fields
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    
    async with async_session() as db:
        fields = await get_fields(db)
    
    if not fields:
        await message.answer("Hozircha bo'sh ish o'rinlari yo'q. Iltimos keyinroq urinib ko'ring.")
        return
        
    keyboard = []
    # 2 buttons per row
    for i in range(0, len(fields), 2):
        row = [KeyboardButton(text=f.name) for f in fields[i:i+2]]
        keyboard.append(row)
        
    kb = ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer("Qaysi yo'nalish bo'yicha ishlamoqchisiz?", reply_markup=kb)
    await state.set_state(CandidateStates.waiting_position)
    
@router.message(CandidateStates.waiting_position)
async def process_position(message: Message, state: FSMContext):
    from db.database import async_session
    from db.crud import create_candidate, get_fields
    
    async with async_session() as db:
        fields = await get_fields(db)
        field = next((f for f in fields if f.name == message.text), None)
        
        if not field:
            await message.answer("Iltimos, quyidagi tugmalardan birini tanlang.")
            return
            
        await state.update_data(field_id=field.id)
        data = await state.get_data()
        
        await create_candidate(
            db,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=data['first_name'],
            last_name=data['last_name'],
            age=data['age'],
            location=data['location'],
            experience=data['experience'],
            field_id=data['field_id'],
            hours_per_day=data['hours'],
            phone_number=data['phone_number']
        )
    
    from aiogram.types import ReplyKeyboardRemove
    await message.answer("Shaxsiy ma'lumotlaringiz saqlandi! Savollar tayyorlanmoqda, iltimos kuting... ⏳", reply_markup=ReplyKeyboardRemove())
    
    await state.set_state(CandidateStates.answering_questions)
    await state.update_data(current_q_index=0, qa_history="")
    
    # Trigger the first question
    from bot.handlers.questions import handle_question_answer
    await handle_question_answer(message, state)
