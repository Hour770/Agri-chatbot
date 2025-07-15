import faiss

def load_database():
    index = faiss.read_index('/Users/cheamenghour/Documents/Cambodia Agriculture/Vector database/data_beta1.faiss')
    return index
