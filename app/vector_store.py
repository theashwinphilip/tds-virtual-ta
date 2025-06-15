import chromadb
from chromadb.utils import embedding_functions
import os
from uuid import uuid4

def create_vector_store(content_dir, discourse_dir, collection_name="tds_data"):
    client = chromadb.Client()
    embedding_function = embedding_functions.DefaultEmbeddingFunction()
    collection = client.create_collection(name=collection_name, embedding_function=embedding_function)
    
    documents = []
    metadatas = []
    ids = []
    
    for filename in os.listdir(content_dir):
        with open(os.path.join(content_dir, filename), 'r', encoding='utf-8') as f:
            text = f.read()
            documents.append(text)
            metadatas.append({"source": "course_content", "filename": filename})
            ids.append(str(uuid4()))
    
    for filename in os.listdir(discourse_dir):
        with open(os.path.join(discourse_dir, filename), 'r', encoding='utf-8') as f:
            text = f.read()
            documents.append(text)
            metadatas.append({"source": "discourse_posts", "filename": filename})
            ids.append(str(uuid4()))
    
    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    print(f"Created vector store with {len(documents)} documents")
    return client, collection

def query_vector_store(client, collection, query_text, n_results=5):
    results = collection.query(query_texts=[query_text], n_results=n_results)
    return results["documents"][0], results["metadatas"][0], results["ids"][0]


if __name__ == "__main__":
    content_dir = "../data/course_content"
    discourse_dir = "../data/discourse_posts"
    client, collection = create_vector_store(content_dir, discourse_dir)
    docs, metas, ids = query_vector_store(client, collection, "gpt-3.5-turbo vs gpt-4o-mini")
    for doc, meta in zip(docs, metas):
        print(f"Source: {meta['source']}, File: {meta['filename']}\nText: {doc[:200]}...")