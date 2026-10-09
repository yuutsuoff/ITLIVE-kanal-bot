from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from bot.states.candidate_states import CandidateStates
from db.database import async_session
from db.crud import create_answer, update_candidate_status, get_candidate_by_telegram_id, get_active_questions
from core.ai_evaluator import evaluate_candidate_answers
from sqlalchemy import select
from db.models import Question, Field
import random

router = Router()

@router.message(CandidateStates.answering_questions)
async def handle_question_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    q_index = data.get('current_q_index', 0)
    qa_history = data.get('qa_history', "")
    current_q_text = data.get('current_q_text')
    question_ids = data.get('question_ids', [])
    
    async with async_session() as db:
        candidate = await get_candidate_by_telegram_id(db, message.from_user.id)
        if not candidate:
            await message.answer("Xatolik: Nomzod topilmadi. /start tugmasini bosing.")
            await state.clear()
            return
            
        # 1. Save the answer to the previous question
        if current_q_text and q_index > 0:
            # For dynamic questions, we use a special ID or just find the last one
            from db.crud import create_answer, create_question
            
            # Since we don't have static IDs anymore, we create a dynamic question record
            # Fetch field name for category
            res = await db.execute(select(Field).where(Field.id == candidate.field_id))
            field = res.scalar_one_or_none()
            field_name = field.name if field else "General"
            
            # Save the question text we just asked to DB so we have an ID for the answer
            db_q = await create_question(db, current_q_text, category=field_name)
            await create_answer(db, candidate.id, db_q.id, message.text)
            
            # Update history for AI
            qa_history += f"Savol: {current_q_text}\nJavob: {message.text}\n\n"
            await state.update_data(qa_history=qa_history)
        
        # 2. Ask next question or finish (Limit: 5 questions)
        MAX_QUESTIONS = 5
        if q_index < MAX_QUESTIONS:
            await message.answer(f"Savol {q_index + 1}/{MAX_QUESTIONS} tayyorlanmoqda... ⏳")
            
            from core.ai_evaluator import generate_next_question
            
            # Prepare candidate info for AI
            cand_info = f"Ism: {candidate.first_name} {candidate.last_name}, " \
                        f"Yosh: {candidate.age}, Manzil: {candidate.location}, " \
                        f"Tajriba: {candidate.experience}, Soha: {field_name if 'field_name' in locals() else 'Noma''lum'}"
            
            next_q_text = await generate_next_question(cand_info, qa_history, q_index + 1)
            
            await message.answer(next_q_text)
            await state.update_data(current_q_index=q_index + 1, current_q_text=next_q_text)
        else:
            # Finished all questions
            try:
                await update_candidate_status(db, candidate.id, 'completed')
                await state.set_state(CandidateStates.completed)
                
                await message.answer("Barcha savollar tugadi! Tizim tahlil qilmoqda... Kuting ⏳")
                
                print(f"Starting AI evaluation for candidate {candidate.id}...")
                eval_result = await evaluate_candidate_answers(qa_history)
                
                if eval_result:
                    from db.crud import create_evaluation
                    eval_data = {
                        "candidate_id": candidate.id,
                        "overall_score": eval_result.get("overall_score", 0),
                        "logic_score": eval_result.get("logic_score"),
                        "technical_score": eval_result.get("technical_score"),
                        "clarity_score": eval_result.get("clarity_score"),
                        "strengths": eval_result.get("strengths", []),
                        "weaknesses": eval_result.get("weaknesses", []),
                        "recommendation": eval_result.get("recommendation", "maybe"),
                        "ai_summary": eval_result.get("summary")
                    }
                    await create_evaluation(db, eval_data)
                    await message.answer("Tahlil yakunlandi! Rahmat. 🎉")
                    
                    # Notify admins
                    from bot.config import ADMIN_IDS
                    report = f"📄 <b>Yangi nomzod tahlili!</b>\n\n" \
                             f"👤 <b>Ism:</b> {candidate.first_name} {candidate.last_name}\n" \
                             f"📊 <b>Umumiy ball:</b> {eval_result.get('overall_score')}/100\n" \
                             f"💡 <b>Mantiq:</b> {eval_result.get('logic_score')}\n" \
                             f"💻 <b>Texnik:</b> {eval_result.get('technical_score')}\n" \
                             f"📝 <b>Xulosa:</b> {eval_result.get('summary')}\n\n" \
                             f"🏁 <b>Tavsiya:</b> #{eval_result.get('recommendation').upper()}"
                    
                    for admin_id in ADMIN_IDS:
                        try:
                            await message.bot.send_message(admin_id, report, parse_mode="HTML")
                        except Exception as admin_err:
                            print(f"Failed to notify admin {admin_id}: {admin_err}")
                else:
                    await message.answer("Javoblaringiz saqlandi. HR menejerlarimiz tez kunda siz bilan bog'lanishadi!")
            except Exception as e:
                import traceback
                print(f"Error in final processing: {e}")
                traceback.print_exc()
                await message.answer("Rahmat! Javoblaringiz qabul qilindi.")
