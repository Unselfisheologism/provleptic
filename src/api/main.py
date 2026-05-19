import streamlit as st
import os
from src.ingest.csv_loader import CSVLoader
from src.ingest.pdf_loader import PDFLoader
from src.ingest.chunker import TextChunker
from src.embed.embedding_service import EmbeddingService
from src.store.vector_store import VectorStore
from src.store.metadata_store import MetadataStore
from src.rag.retriever import Retriever
from src.rag.generator import Generator
from loguru import logger

# Initialize services
@st.cache_resource
def get_services():
    chunker = TextChunker()
    csv_loader = CSVLoader(chunker)
    pdf_loader = PDFLoader(chunker)
    embedding_service = EmbeddingService()
    vector_store = VectorStore()
    metadata_store = MetadataStore()
    retriever = Retriever(vector_store, embedding_service)
    generator = Generator()
    return csv_loader, pdf_loader, vector_store, metadata_store, retriever, generator

csv_loader, pdf_loader, vector_store, metadata_store, retriever, generator = get_services()

st.set_page_config(page_title="Indian Public Data RAG", page_icon="🇮🇳")

st.title("🇮🇳 Sovereign RAG for Indian Public Data")
st.markdown("""
This tool allows you to query Indian public datasets (CSV/PDF) using natural language.
All processing is local-first, with citations to exact source rows/pages.
""")

with st.sidebar:
    st.header("Data Ingestion")
    uploaded_file = st.file_uploader("Upload a CSV or PDF file", type=["csv", "pdf"])
    source_url = st.text_input("Source URL (optional)", value="local")
    
    if st.button("Process & Ingest"):
        if uploaded_file:
            # Save to raw data dir
            raw_path = os.path.join("data/raw", uploaded_file.name)
            os.makedirs("data/raw", exist_ok=True)
            with open(raw_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            with st.spinner("Processing..."):
                if uploaded_file.name.endswith(".csv"):
                    chunks = csv_loader.load(raw_path, source_url)
                else:
                    chunks = pdf_loader.load(raw_path, source_url)
                
                vector_store.add_documents(chunks)
                
                # Log to metadata store
                if chunks:
                    meta = chunks[0]['metadata']
                    metadata_store.log_ingestion(
                        file_name=uploaded_file.name,
                        source_url=source_url,
                        ingested_at=meta['ingested_at'],
                        content_hash=meta['content_hash']
                    )
                
                st.success(f"Ingested {len(chunks)} chunks from {uploaded_file.name}")
        else:
            st.error("Please upload a file first.")

    st.header("Ingested Data")
    ingestions = metadata_store.get_all_ingestions()
    for ing in ingestions:
        st.text(f"📄 {ing[1]}")

st.header("Ask a Question")
question = st.text_input("e.g., Which district in Maharashtra had highest PMAY fund utilization?")

if st.button("Query"):
    if question:
        with st.spinner("Searching and generating answer..."):
            context_chunks = retriever.retrieve(question)
            if not context_chunks:
                st.warning("No relevant data found. Please ingest some data first.")
            else:
                result = generator.generate_answer(question, context_chunks)
                
                st.markdown("### Answer")
                st.write(result['answer'])
                
                st.markdown(f"**Confidence Score:** {result['confidence_score']:.2f}")
                
                with st.expander("Sources & Context"):
                    for i, chunk in enumerate(context_chunks):
                        st.markdown(f"**Source {i+1}**")
                        st.json(chunk['metadata'])
                        st.text(chunk['content'])
    else:
        st.error("Please enter a question.")
