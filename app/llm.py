from openai import OpenAI
from typing import List, Dict
from app.config import OPENAI_API_KEY

class LLMHandler:
    """Handles LLM interactions for generating answers"""
    
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
    
    def generate_answer(self, query: str, context_chunks: List[Dict]) -> str:
        """Generate an answer based on the query and retrieved context"""
        
        # Prepare context from retrieved chunks
        context = "\n\n".join([
            f"Source {i+1} (from {chunk['metadata']['url']}):\n{chunk['content']}"
            for i, chunk in enumerate(context_chunks)
        ])
        
        # Create prompt
        prompt = f"""You are a helpful assistant that answers questions based on the provided context.
Use only the information from the context below to answer the question. If you cannot answer the question based on the context, say so.

Context:
{context}

Question: {query}

Answer:"""
        
        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that provides accurate answers based on given context."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content
            return answer
        
        except Exception as e:
            return f"Error generating answer: {str(e)}"
    
    def generate_answer_with_sources(self, query: str, context_chunks: List[Dict]) -> Dict:
        """Generate an answer with source citations"""
        answer = self.generate_answer(query, context_chunks)
        
        # Extract unique sources
        sources = list(set([chunk['metadata']['url'] for chunk in context_chunks]))
        
        return {
            "answer": answer,
            "sources": sources,
            "num_sources": len(sources)
        }
