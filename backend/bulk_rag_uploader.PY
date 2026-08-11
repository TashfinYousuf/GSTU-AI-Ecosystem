import os
import glob
import time
from dotenv import load_dotenv
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
INDEX_NAME = "gstu-knowledge-base" # Pinecone ইনডেক্স

def bulk_upload_to_vectordb(directory_path: str):
    print(f"🚀 Starting Bulk RAG Upload from: {directory_path}")
    
    # 1. ফাইন্ড অল পিডিএফ
    pdf_files = glob.glob(f"{directory_path}/**/*.pdf", recursive=True)
    if not pdf_files:
        print("❌ No PDFs found!")
        return

    print(f"📚 Found {len(pdf_files)} PDFs. Extracting text...")
    
    all_docs = []
    for pdf_path in pdf_files:
        try:
            loader = PyMuPDFLoader(pdf_path)
            docs = loader.load()
            
            # মেটাডেটাতে সোর্স অ্যাড করা
            for doc in docs:
                doc.metadata["source"] = os.path.basename(pdf_path)
                doc.metadata["type"] = "academic_resource"
                
            all_docs.extend(docs)
            print(f"✔️ Loaded: {os.path.basename(pdf_path)}")
        except Exception as e:
            print(f"⚠️ Skipped {pdf_path}: {e}")

    # 2. চাংকিং (Chunking)
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = [c for c in splitter.split_documents(all_docs) if c.page_content.strip()]
    print(f"✂️ Total Chunks created: {len(chunks)}")

    # 3. এমবেডিং ও পাইনকোন আপলোড
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2", google_api_key=GOOGLE_API_KEY)
    
    BATCH_SIZE = 50
    total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE

    print(f"☁️ Uploading to Pinecone '{INDEX_NAME}' in {total_batches} batches...")

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        try:
            PineconeVectorStore.from_documents(documents=batch, embedding=embeddings, index_name=INDEX_NAME, pinecone_api_key=PINECONE_API_KEY)
            print(f"  ✅ Uploaded Batch {batch_num}/{total_batches}")
            time.sleep(2) # Google API Rate Limit বাইপাস করার জন্য
        except Exception as e:
            print(f"  ❌ Failed Batch {batch_num}: {e}")

    print("🎉 BULK UPLOAD COMPLETE! All data is securely in the Vector DB. You can safely delete the local PDFs now.")

if __name__ == "__main__":
    # কম্পিউটারের যে কোনো ডিরেক্টরি পাথ ব্যবহার করা যাবে। উদাহরণস্বরূপ: "./department_files_to_upload"
    TARGET_DIR = "/Users/tashfinyousuf/Python/GSTU_IR_AI/data" 
    
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)
        print(f"📁 Created folder '{TARGET_DIR}'. Put your PDFs inside and run again.")
    else:
        bulk_upload_to_vectordb(TARGET_DIR)