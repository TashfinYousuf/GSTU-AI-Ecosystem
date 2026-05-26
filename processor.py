import os
import time
import gc
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from supabase import create_client

load_dotenv()

def process_and_upload_data(data_folder="university_data"):
    print("🚀 Initializing Supabase Cloud DB Connection...")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") 
    
    if not supabase_url or not supabase_key:
        print("⚠️ Error: Supabase credentials missing in .env file!")
        return

    supabase = create_client(supabase_url, supabase_key)
    
    # 🔴 FIX: CPU Threads limit kore dewa holo jate Mac gorom na hoy
    print("⚙️ Loading Embedding Model (Optimized for low CPU usage)...")
    embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5", threads=2)
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    
    print(f"📂 Scanning folder: {data_folder}...")
    
    for root, dirs, files in os.walk(data_folder):
        for file in files:
            if file.endswith(".pdf"):
                file_path = os.path.join(root, file)
                print(f"📄 Processing: {file} ...")
                
                try:
                    loader = PyPDFLoader(file_path)
                    docs = loader.load()
                    
                    course_name = os.path.basename(root)
                    for doc in docs:
                        doc.metadata["course"] = course_name
                        
                    splits = text_splitter.split_documents(docs)
                    
                    if splits:
                        print(f"⏳ Uploading {len(splits)} chunks for {file} to Supabase...")
                        SupabaseVectorStore.from_documents(
                            splits,
                            embeddings,
                            client=supabase,
                            table_name="gstu_documents",
                            query_name="match_documents"
                        )
                        print(f"✅ Successfully uploaded: {file}")
                        
                    # 🔴 RAM theke garbage clear kora ar CPU ke thanda howar shomoy dewa
                    del docs
                    del splits
                    gc.collect()
                    time.sleep(2) # 2 seconds rest for CPU
                    
                except Exception as e:
                    print(f"❌ Error processing {file}: {e}")
                    
    print("🎉 ALL DONE! All data successfully uploaded to Supabase Cloud!")

if __name__ == "__main__":
    process_and_upload_data()