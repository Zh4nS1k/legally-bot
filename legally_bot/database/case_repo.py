
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

class CaseRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        # Collections
        self.cases = db.cases                 # Admin Library of Questions
        self.student_cases = db.student_cases # Assigned to Student
        self.professor_cases = db.professor_cases # Assigned to Professor (or escalated)
        self.rated_questions = db.rated_questions # Final Rated Data
        self.chat_questions = db.chat_questions # Regular Chat History

    async def log_chat_question(self, user_id, question, answer, chunks, articles):
        """Logs normal chat interactions."""
        await self.chat_questions.insert_one({
            "user_id": user_id,
            "question": question,
            "answer": answer,
            "chunks": chunks,
            "articles": articles,
            "timestamp": datetime.utcnow()
        })

    async def save_admin_cases(self, cases_data: list, saver_id: int):
        """Saves a batch of questions uploaded by Admin/Dev."""
        documents = []
        for case in cases_data:
            documents.append({
                "question": case['question'],
                "answer": case['ai_answer'],
                "chunks": case['chunks'],
                "articles": case['articles'],
                "saved_by": saver_id,
                "saved_at": datetime.utcnow(),
                "subject": case.get('subject', 'General'),
                "status": "new"
            })
        if documents:
            await self.cases.insert_many(documents)
            logging.info(f"💾 Saved {len(documents)} cases to Admin Library.")

    async def assign_case_to_student(self, case_id, student_id):
        """Copies a case to student_cases."""
        case = await self.cases.find_one({"_id": case_id})
        if not case:
            return False
        
        # Create assignment
        assignment = case.copy()
        assignment["original_case_id"] = case["_id"]
        assignment["assigned_to"] = student_id
        assignment["assigned_at"] = datetime.utcnow()
        assignment["status"] = "assigned"
        del assignment["_id"] # New ID for assignment
        
        await self.student_cases.insert_one(assignment)
        return True

    async def assign_case_to_professor(self, case_id, professor_id, from_collection="cases"):
        """Copies a case to professor_cases."""
        # Can be from 'cases' (direct assignment) or 'student_cases' (escalation)
        if from_collection == "cases":
            source_col = self.cases
        elif from_collection == "student_cases":
            source_col = self.student_cases
        else:
            return False

        case = await source_col.find_one({"_id": case_id})
        if not case:
            return False

        assignment = case.copy()
        assignment["assigned_to"] = professor_id
        assignment["assigned_at"] = datetime.utcnow()
        assignment["status"] = "assigned"
        if "_id" in assignment:
             del assignment["_id"]
             
        await self.professor_cases.insert_one(assignment)
        return True

    async def submit_rating(self, collection_name, case_id, ratings, comment, rater_id):
        """
        Updates the case with ratings and copies to rated_questions.
        collection_name: 'student_cases' or 'professor_cases'
        """
        collection = self.db[collection_name]
        
        update_data = {
            "ratings": ratings, # {question: 0-10, chunk: 0-10, article: 0-10}
            "comment": comment,
            "rated_by": rater_id,
            "rated_at": datetime.utcnow(),
            "status": "rated"
        }
        
        await collection.update_one({"_id": case_id}, {"$set": update_data})
        
        # Copy to Global Rated Collection
        rated_doc = await collection.find_one({"_id": case_id})
        if rated_doc:
            rated_doc["original_collection"] = collection_name
            del rated_doc["_id"]
            await self.rated_questions.insert_one(rated_doc)
            
        return True
