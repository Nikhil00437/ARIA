# rag.py
import os
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

def run_rag(query: str, data_dir: str = "scraped_data", model: str = "your-model-name"):
    loader = DirectoryLoader(data_dir, glob="*.md")
    docs = loader.load()
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = splitter.split_documents(docs)
    
    embedder = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = Chroma.from_documents(chunks, embedder)
    retriever = db.as_retriever(search_kwargs={"k": 3})
    
    prompt = ChatPromptTemplate.from_template(
        "Answer using context only. Cite source if possible.\nContext: {context}\nQuestion: {query}"
    )
    llm = ChatOpenAI(model=model, base_url="http://localhost:1234/v1", api_key="not-needed")
    chain = prompt | llm | StrOutputParser()
    
    context = retriever.invoke(query)
    ctx_text = "\n\n".join([d.page_content for d in context])
    return chain.invoke({"context": ctx_text, "query": query})

if __name__ == "__main__":
    print(run_rag("what is Claude Mythos?", model="qwen/qwen3.5-9b"))