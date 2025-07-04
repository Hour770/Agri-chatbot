import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
import os

embeddings_model = SentenceTransformer('distiluse-base-multilingual-cased')


def load_chunks_from_file(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Split on "--- Chunk"
    raw_chunks = text.split('--- Chunk')[1:]  # skip the header before first chunk
    chunks = ["--- Chunk" + chunk.strip() for chunk in raw_chunks if chunk.strip()]
    return chunks

# Load your saved FAISS index and chunk list
index = faiss.read_index('/Users/cheamenghour/Documents/Cambodia Agriculture/Vector database/khmer_agri_index.faiss')
chunks = load_chunks_from_file('/Users/cheamenghour/Documents/Cambodia Agriculture/All_chunks/all_chunks.txt')

def retrieve_context(query, top_k=5):
    query_embedding = embeddings_model.encode([query])
    D, I = index.search(np.array(query_embedding), top_k)
    return [chunks[i] for i in I[0]]

# Create chat prompt 
def build_prompt(query, context_chunks):
    context = "\n\n".join(context_chunks)
    return f"""You are an agricultural assistant for Cambodia.
Answer the following question using the provided context.

Context:
{context}

Question: {query}

Answer:"""


# Replace with your actual Gemini API key
API_KEY = "AIzaSyCd_OYN8dgWEGnEb7PhDnMNyKQe7zvSs8o"  
genai.configure(api_key=API_KEY)

# Load the Gemini model
model = genai.GenerativeModel('gemini-1.5-flash')

def query_gemini(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print("Error:", e)
        return "Sorry, something went wrong."

# Example question from user
user_query = "ប្រាប់ខ្ញុំអំពីការប្រើប្រាស់ជីរបស់ស្រូវស្បៃមង្គល"

# Retrieve context from vector DB
context_chunks = retrieve_context(user_query)

# Build prompt
prompt = build_prompt(user_query, context_chunks)

# Call Gemini API
response = query_gemini(prompt)

# Show response
print("Answer:")
print(response)