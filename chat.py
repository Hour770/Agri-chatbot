import numpy as np
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from load_database import load_database

embeddings_model = SentenceTransformer('distiluse-base-multilingual-cased')

def load_chunks_from_file(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
        
    # Split on "--- Chunk"
    raw_chunks = text.split('--- Chunk')[1:]  # skip the header before first chunk
    chunks = ["--- Chunk" + chunk.strip() for chunk in raw_chunks if chunk.strip()]
    return chunks

# Load your saved FAISS index and chunk list
index = load_database()
chunks = load_chunks_from_file('/Users/cheamenghour/Documents/Cambodia Agriculture/All_chunks/all_chunks.txt')

def retrieve_context(query, top_k=5):
    query_embedding = embeddings_model.encode([query])
    D, I = index.search(np.array(query_embedding), top_k)
    return [chunks[i] for i in I[0]]

# Create chat prompt 
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

# Replace with your actual Gemini API key
API_KEY = "AIzaSyCd_OYN8dgWEGnEb7PhDnMNyKQe7zvSs8o"  
genai.configure(api_key=API_KEY)

# Load the Gemini model
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