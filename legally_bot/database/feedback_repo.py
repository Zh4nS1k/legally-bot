from legally_bot.database.mongo_db import db
from datetime import datetime
from bson.objectid import ObjectId

class FeedbackRepository:
    cases_collection = "cases"
    feedback_collection = "feedback_logs"

    # --- Cases ---
    @classmethod
    async def get_random_case(cls, domain: str = None):
        """Fetches a random case, optionally filtered by domain."""
        pipeline = [{"$sample": {"size": 1}}]
        if domain:
            pipeline.insert(0, {"$match": {"domain": domain}})
        
        cursor = db.get_db()[cls.cases_collection].aggregate(pipeline)
        cases = await cursor.to_list(length=1)
        return cases[0] if cases else None

    @classmethod
    async def create_case(cls, text: str, domain: str, difficulty: str):
        case_data = {
            "text": text,
            "domain": domain,
            "difficulty": difficulty,
            "created_at": datetime.utcnow()
        }
        result = await db.get_db()[cls.cases_collection].insert_one(case_data)
        return str(result.inserted_id)

    # --- Feedback ---
    @classmethod
    async def log_feedback(cls, student_id: int, case_id: str, ai_response_id: str,
                          rating: int = None, error_type: str = None, 
                          student_comment: str = None):
        feedback_data = {
            "student_id": student_id,
            "case_id": ObjectId(case_id) if case_id else None,
            "ai_response_id": ai_response_id,
            "rating_score": rating,
            "error_type": error_type,
            "student_comment": student_comment,
            "professor_validation_status": "pending" if error_type else "approved", # If no error, auto-approve
            "created_at": datetime.utcnow()
        }
        await db.get_db()[cls.feedback_collection].insert_one(feedback_data)

    @classmethod
    async def get_pending_feedback(cls):
        cursor = db.get_db()[cls.feedback_collection].find({"professor_validation_status": "pending"})
        return await cursor.to_list(length=50)

    @classmethod
    async def validate_feedback(cls, feedback_id: str, status: str): # status: approved/rejected
        await db.get_db()[cls.feedback_collection].update_one(
            {"_id": ObjectId(feedback_id)},
            {"$set": {"professor_validation_status": status}}
        )
