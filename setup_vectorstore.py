import os
import time
from dotenv import load_dotenv
from openai import OpenAI

# Load .env into environment variables
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not found. Put it in .env")

client = OpenAI(api_key=api_key)

BOOK_PATH = "/Users/Joseph/Documents/automation/summarization/INNER SENSE.pdf"  # put your file here

# 1) Create vector store
vector_store = client.vector_stores.create(name="INNER_SENSE_PDF")
print("Vector store ID:", vector_store.id)

# 2) Upload book file
with open(BOOK_PATH, "rb") as f:
    uploaded = client.files.create(file=f, purpose="assistants")
print("File ID:", uploaded.id)

# 3) Attach file to vector store (starts indexing)
client.vector_stores.files.create(
    vector_store_id=vector_store.id,
    file_id=uploaded.id,
)
print("Indexing started...")

# 4) Poll until indexing is complete
while True:
    vs = client.vector_stores.retrieve(vector_store.id)
    status = getattr(vs, "status", None)
    if status == "completed":
        print("Indexing completed.")
        break
    if status == "failed":
        raise RuntimeError("Vector store indexing failed.")
    print("Waiting... status =", status)
    time.sleep(2)

print("READY: use this vector_store_id in your Eval tool config:")
print(vector_store.id)
