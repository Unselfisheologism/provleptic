from src.core.opencode_client import opencode_client
from src.rag.prompt import format_prompt
from loguru import logger

class Generator:
    def __init__(self, model: str = "gpt-3.5-turbo"):
        self.model = model

    def generate_answer(self, question: str, context_chunks: list):
        prompt = format_prompt(question, context_chunks)
        
        logger.info(f"Generating answer for question: {question}")
        
        response = opencode_client.request_with_retry(
            "chat",
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Question: {question}"}
            ],
            temperature=0
        )
        
        answer = response.choices[0].message.content
        
        # Simple confidence score logic (dummy for now as LLMs don't return it directly easily)
        # In a real scenario, you might use logprobs or another model to evaluate.
        confidence_score = 0.85 # Placeholder
        
        return {
            "answer": answer,
            "confidence_score": confidence_score,
            "sources": [chunk['metadata'] for chunk in context_chunks]
        }
