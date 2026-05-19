RAG_SYSTEM_PROMPT = """You are an analyst answering questions about Indian public data.
Answer concisely. ALWAYS cite the exact source (file name, page/row number).
If unsure, say "I cannot find this in the provided data."

Context:
{context}
"""

def format_prompt(question: str, context_chunks: list) -> str:
    context_text = ""
    for i, chunk in enumerate(context_chunks):
        source = chunk['metadata'].get('source', 'Unknown')
        page = chunk['metadata'].get('page_number', 'N/A')
        row = chunk['metadata'].get('row_number', 'N/A')
        context_text += f"[{i+1}] Source: {source}, Page: {page}, Row: {row}\nContent: {chunk['content']}\n\n"
    
    return RAG_SYSTEM_PROMPT.format(context=context_text)
