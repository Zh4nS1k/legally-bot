from aiogram.fsm.state import State, StatesGroup

class RegistrationState(StatesGroup):
    waiting_for_language = State()
    waiting_for_name = State()
    waiting_for_email = State()
    waiting_for_code = State()
    waiting_for_role = State()

class IngestionState(StatesGroup):
    waiting_for_file = State()
    waiting_for_url = State()

class StudentModeState(StatesGroup):
    waiting_for_feedback = State()
    waiting_for_rating = State()
    waiting_for_error_desc = State()

class ChatState(StatesGroup):
    chatting = State()
    waiting_for_comment = State()

class ReviewState(StatesGroup):
    viewing_queue = State()

class AdminStates(StatesGroup):
    waiting_for_case_file = State()
    waiting_for_assignee = State()
    waiting_for_case_id = State()
