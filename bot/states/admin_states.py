from aiogram.fsm.state import StatesGroup, State

class AdminStates(StatesGroup):
    waiting_question_text = State()
    waiting_question_category = State()
    waiting_question_difficulty = State()
