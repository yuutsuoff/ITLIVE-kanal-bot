from aiogram.fsm.state import StatesGroup, State

class CandidateStates(StatesGroup):
    # Ro'yxatdan o'tish
    waiting_contact       = State()
    waiting_first_name    = State()
    waiting_last_name     = State()
    waiting_age           = State()
    waiting_location      = State()
    waiting_experience    = State()
    waiting_exp_detail    = State()
    waiting_hours         = State()
    waiting_position      = State()
    
    # Savollar bosqichi
    answering_questions   = State()
    
    # Tugagan
    completed             = State()
