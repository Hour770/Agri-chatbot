import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

# Load embedding model
embeddings_model = SentenceTransformer('distiluse-base-multilingual-cased')

# Define alias replacements (extendable)
alias_map = {
    "ស្រូវស្បៃមង្គល": "ស្រូវដំណើបស្បៃមង្គល",
    # Add more known synonyms here if needed
}

def normalize_query(query):
    """Replace known aliases to ensure consistent search"""
    for k, v in alias_map.items():
        if k in query:
            return query.replace(k, v)
    return query

def load_chunks_from_file(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    raw_chunks = text.split('--- Chunk')[1:]
    chunks = ["--- Chunk" + chunk.strip() for chunk in raw_chunks if chunk.strip()]
    return chunks

# Load FAISS index and chunks at startup
index = faiss.read_index('khmer_agri_index.faiss')
chunks = load_chunks_from_file('all_chunks.txt')
chunk_embeddings = embeddings_model.encode(chunks, normalize_embeddings=True)

def retrieve_context(query, top_k=5, boost_score=0.2):
    query = normalize_query(query)
    query_embedding = embeddings_model.encode([query], normalize_embeddings=True)

    # Perform FAISS semantic search
    D, I = index.search(np.array(query_embedding), top_k)
    results = []

    for i, idx in enumerate(I[0]):
        score = 1 - D[0][i]  # Convert L2 distance to similarity
        chunk = chunks[idx]

        # Boost if query text appears directly in chunk
        if query in chunk or any(part in chunk for part in query.split()):
            score += boost_score

        results.append((chunk, score))

    # Sort and return top_k chunks
    results.sort(key=lambda x: x[1], reverse=True)
    return [chunk for chunk, _ in results[:top_k]]

def build_prompt(query, context_chunks):
    context = "\n\n".join(context_chunks)
    return f"""You are an agricultural assistant for Cambodia.
Answer the following question using the provided context.

Remember that you can't answer based on your own understanding, you must 100% follow through our provided context. If in case you can't find any relative information
from our context to answer the question, you should find the most closely related one to the question.

Context:
{context}

Question: {query}

Answer:"""

# Gemini API setup
genai.configure(api_key="AIzaSyCd_OYN8dgWEGnEb7PhDnMNyKQe7zvSs8o")
model = genai.GenerativeModel('gemini-1.5-flash')

def query_chatbot(user_query):
    try:
        context_chunks = retrieve_context(user_query)
        prompt = build_prompt(user_query, context_chunks)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print("Error:", e)
        return "Sorry, something went wrong."
