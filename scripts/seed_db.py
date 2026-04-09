"""
scripts/seed_db.py
------------------
Seeds the PostgreSQL database with initial curriculum data (Modules, Topics, etc.).
"""

import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import async_session
from src.models.content import Module, Topic, BloomLevel, DifficultyBucket, Question, CorrectAnswer, QuestionStatus

async def seed():
    async with async_session() as db:
        print("Seeding initial curriculum...")
        
        # 1. Module
        module1 = Module(
            id=uuid.uuid4(),
            name="Deep Learning Foundations",
            description="Core concepts of neural networks and deep learning.",
            order_index=1
        )
        db.add(module1)
        await db.flush()

        # 2. Topic
        topic1 = Topic(
            id=uuid.uuid4(),
            module_id=module1.id,
            name="Neural Network Basics",
            description="Introduction to architecture, neurons, and layers.",
            order_index=1
        )
        db.add(topic1)
        await db.flush()

        # 3. Question
        question1 = Question(
            item_id="ITEM-001-00001",
            module_id=module1.id,
            topic_id=topic1.id,
            bloom_level=BloomLevel.remember,
            difficulty_bucket=DifficultyBucket.easy,
            status=QuestionStatus.active,
            stem_text="What is the primary activation function used in the hidden layers of modern deep neural networks?",
            option_a="ReLU",
            option_b="Sigmoid",
            option_c="Tanh",
            option_d="Step",
            correct_answer=CorrectAnswer.A,
            explanation_text="ReLU (Rectified Linear Unit) is widely used due to its computational efficiency and reduction of the vanishing gradient problem."
        )
        db.add(question1)

        await db.commit()
        print("Seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed())
