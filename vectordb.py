with open(
    r"C:\Users\dell\Desktop\telecom_data.txt",
    "r",
    encoding="utf-8"
) as file:
    telecom_text = file.read()

from langchain_text_splitters import CharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma



text_splitter = CharacterTextSplitter(
    separator="\n",
    chunk_size=300,      
    chunk_overlap=50     
)
chunks = text_splitter.split_text(telecom_text)

print(f"Total Chunks Created: {len(chunks)}")

from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma


embeddings = OllamaEmbeddings(model="nomic-embed-text")


vector_db = Chroma.from_texts(
    texts=chunks,
    embedding=embeddings,
    persist_directory="./telecom_vector_db"
)

vector_db.persist()

query = "How can I recharge my prepaid plan?"

results = vector_db.similarity_search(query, k=2)

print("Query:", query)
print("\nTop Relevant Chunks:")
for i, doc in enumerate(results, 1):
    print(f"{i}. {doc.page_content}")
