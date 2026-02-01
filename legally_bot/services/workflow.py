from legally_bot.database.users_repo import UserRepository
from legally_bot.database.feedback_repo import FeedbackRepository
from legally_bot.services.rag_engine import RAGEngine

rag = RAGEngine()

class WorkflowService:
    
    @staticmethod
    async def process_student_question(user_id: int, question: str):
        # 1. Check if user is student ?? (handled in handler)
        # 2. Get answer from RAG
        result = await rag.search(question)
        
        # 3. Save interaction ?? (Optional, depending on detailed logging requirements)
        # For now, we return the result to the handler to display
        return result

    @staticmethod
    async def submit_feedback(user_id: int, case_id: str, ai_response_id: str, rating: int, error_type: str, comment: str):
        await FeedbackRepository.log_feedback(
            student_id=user_id,
            case_id=case_id,
            ai_response_id=ai_response_id,
            rating=rating,
            error_type=error_type,
            student_comment=comment
        )
        
        if rating and rating > 7:
            # Good job, increment stats
            await UserRepository.increment_cases_solved(user_id)

    @staticmethod
    async def get_professor_queue():
        return await FeedbackRepository.get_pending_feedback()

    @staticmethod
    async def approve_correction(feedback_id: str, professor_id: int):
        await FeedbackRepository.validate_feedback(feedback_id, "approved")
        # Logic to retrain/add to dataset could go here
    
    @staticmethod
    async def reject_correction(feedback_id: str, professor_id: int):
        await FeedbackRepository.validate_feedback(feedback_id, "rejected")
