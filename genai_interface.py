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
    return f"""អ្នកគឺជជំនួយការផ្នែកកសិកម្មសម្រាប់ប្រទេសកម្ពុជា។
អ្នកត្រូវឆ្លើយសំណួរខាងក្រោមដោយផ្អែកលើបរិបទដែលបានផ្ដល់ជូន។

***សូមចងចាំថាអ្នកមិនត្រូវឆ្លើយតាមចំណេះដឹងផ្ទាល់ខ្លួនទេ។ អ្នកត្រូវឆ្លើយតែអ្វីដែលមាននៅក្នុងបរិបទតែប៉ុណ្ណោះ។***
បើសិនជាអ្នករកមិនឃើញព័ត៍មានដ៏ពាក់ព័ន្ធនឹងសំណួរនោះទេ សូមឆ្លើយតែអ្វីដែលពាក់ព័ន្ធជិតស្និទ្ធបំផុតបំផុតជាមួយនឹងសំណួរនោះ។

បរិបទ៖
{context}

សំណួរ៖ {query}

ចម្លើយ៖"""

# Gemini API setup
genai.configure(api_key="AIzaSyD2V_GZIpxaGOI1JcEIuUTudxiTWPdk1ts")
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
