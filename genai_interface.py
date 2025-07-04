import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

embeddings_model = SentenceTransformer('distiluse-base-multilingual-cased')

def load_chunks_from_file(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    raw_chunks = text.split('--- Chunk')[1:]
    chunks = ["--- Chunk" + chunk.strip() for chunk in raw_chunks if chunk.strip()]
    return chunks

# Load FAISS index + chunks only once at startup
index = faiss.read_index('khmer_agri_index.faiss')
chunks = load_chunks_from_file('all_chunks.txt')

def retrieve_context(query, top_k=5):
    query_embedding = embeddings_model.encode([query])
    D, I = index.search(np.array(query_embedding), top_k)
    return [chunks[i] for i in I[0]]

def build_prompt(query, context_chunks):
    context = "\n\n".join(context_chunks)
    return f"""You are an agricultural assistant for Cambodia.
Answer the following question using the provided context.

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
