# prompts/llm_prompts.py
# This module defines the LLMPrompts class.
# Prompt engineering is the practice of structuring text inputs (prompts) to guide LLM behavior.
# This class acts as a centralized repository of template methods returning formatted prompts.
# It uses standard Python f-strings to inject user queries, history, and document snippets dynamically.

from typing import Dict


class LLMPrompts:
    """
    Static collection of prompt templates for various multi-agent tasks.
    Each method takes parameters and formats them into instructions for the LLM.
    """
    
    @staticmethod
    def summarization(text: str, context: str = "") -> str:
        """
        Creates a prompt asking the model to summarize a document while respecting chat history context.
        """
        return f"""Summarize the following text using key facts from the context.
Format in markdown:
- **Summary**: Concise high-level summary.
- **Key Points**: Bulleted list of critical details (numeric values, dates, etc.).

Question: {text}
Context: {context}
Keep it concise and factual."""
                
    @staticmethod
    def code_generation(description: str, language: str = "python") -> str:
        """
        Creates a prompt asking the model to write code in a specific language (e.g. Python, SQL).
        """
        return f"""Generate {language} code for the following task:
{description}
Code:"""
                      
    @staticmethod
    def question_answering(question: str, context: str = "") -> str:
        """
        Standard question-answering prompt instructing the model to answer using only context facts.
        """
        return f"""Answer the following question using only the context provided.
Format as brief Markdown.

Context: {context}
Question: {question}
Answer:"""
                  
    @staticmethod
    def reasoning(problem: str) -> str:
        """
        Forces the model to think step-by-step (Chain-of-Thought reasoning).
        This improves accuracy for math, logic, or programming questions.
        """
        return f"""Solve the following problem step by step.
Format final answer in bold Markdown.

Problem: {problem}
Solution:"""
                  
    @staticmethod
    def chat_summary(user_message: str, conversation_history: str = "") -> str:
        """
        Creates a prompt for generating general conversational responses while preserving thread context.
        """
        history_section = f"\nHistory:\n{conversation_history}\n" if conversation_history else ""

        return f"""You are a helpful AI assistant. Provide a clear response.
{history_section}
User Question: {user_message}
Response:"""

    @staticmethod
    def grounded_answer(
        user_message: str,
        retrieved_documents: str,
        conversation_history: str = "",
    ) -> str:
        """
        Prompts the model to answer queries based strictly on retrieved Supabase documents (RAG grounding).
        Limits hallucinations by forcing the model to state if facts are missing.
        """
        history_section = f"\nHistory:\n{conversation_history}\n" if conversation_history else ""

        return f"""You are a formal AI assistant. Answer the user question based strictly on the provided retrieved documents context.

Formatting Guidelines:
- Provide ONE cohesive, highly professional, structured answer using standard Markdown (bullet points, bold emphasis for key facts, and clear paragraphs).
- Do NOT separate your response into artificial headings like "Direct Answer", "Details", or "Sources".
- Incorporate all pertinent facts, dates, and numbers naturally.
- If the requested information is missing from the retrieved documents context, state that clearly and politely in your response.

User Question: {user_message}

Retrieved Documents Context:
{retrieved_documents}
{history_section}"""
             
    @staticmethod
    def get_all_templates() -> Dict[str, str]:
        """Returns description mappings for all templates in our repository."""
        return {
            "summarization": "Summarize text concisely with optional context",
            "code_generation": "Generate code in specified programming language",
            "question_answering": "Answer questions based on provided context",
            "reasoning": "Solve complex problems with step-by-step reasoning",
            "chat_summary": "Generate conversational responses with history awareness",
            "routing_decision": "Determine which agent(s) should handle a user request",
        }
        
    @staticmethod
    def custom_prompt(template: str, **kwargs) -> str:
        """
        Create a custom prompt from a template string with variable substitution.
        
        Example:
            >>> template = "Translate {text} to {language}"
            >>> LLMPrompts.custom_prompt(template, text="Hello", language="French")
            'Translate Hello to French'
        """
        return template.format(**kwargs)
    
        
    @staticmethod
    def routing_decision(user_message: str) -> str:
        """
        Prompts the supervisor agent to perform classification on a user message,
        routing it to 'greeting', 'search', or 'parallel' paths.
        """
        return f"""Analyze this user message and determine the best routing:

Message: "{user_message}"

Routing Options:
- greeting: Simple greetings like "hello", "hi", "hey"
- search: ONLY when user explicitly wants to see raw documents (e.g., "show me documents", "list documents")
- parallel: ALL questions that need answers from documents (e.g., "What is X?", "How much?", "Tell me about Y")

IMPORTANT: Questions asking for information should use "parallel" to search documents AND generate an answer.

Answer with ONE word only (greeting/search/parallel):"""