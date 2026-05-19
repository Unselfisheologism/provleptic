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
from src.ontology.extractor import OntologyExtractor
from src.ontology.graph_store import GraphStore
from src.ontology.nl_to_graph import GraphQueryTranslator
from src.ontology.lineage import LineageTracker
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
    ontology_extractor = OntologyExtractor()
    graph_store = GraphStore()
    query_translator = GraphQueryTranslator(graph_store.get_graph())
    lineage_tracker = LineageTracker(metadata_store)
    return csv_loader, pdf_loader, vector_store, metadata_store, retriever, generator, ontology_extractor, graph_store, query_translator, lineage_tracker

csv_loader, pdf_loader, vector_store, metadata_store, retriever, generator, ontology_extractor, graph_store, query_translator, lineage_tracker = get_services()

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
                
                # Ontology Extraction
                with st.spinner("Building Ontology Graph..."):
                    for chunk in chunks:
                        chunk_id = f"{chunk['metadata']['content_hash']}_{chunk['metadata']['chunk_index']}"
                        extraction = ontology_extractor.extract(chunk['content'], chunk_id)
                        for node in extraction.nodes:
                            graph_store.add_node(node)
                        for edge in extraction.edges:
                            graph_store.add_edge(edge)
                
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

st.header("Interactions")
tab1, tab2, tab3 = st.tabs(["🔍 Q&A", "🕸️ Ontology Query", "📊 Visualize"])

with tab1:
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

with tab2:
    ont_query = st.text_input("Ask about relationships (e.g., Show schemes for farmers in Maharashtra)")
    if st.button("Search Graph"):
        if ont_query:
            with st.spinner("Querying graph..."):
                results = query_translator.query(ont_query)
                for res in results:
                    with st.expander(f"Entity: {res.get('name', res['id'])}"):
                        st.json(res)
                        if "source_chunk_id" in res:
                            lineage = lineage_tracker.get_source_details(res["source_chunk_id"])
                            st.markdown("**Lineage Info:**")
                            st.json(lineage)
        else:
            st.error("Please enter a graph query.")

with tab3:
    st.markdown("### Interactive Ontology Graph")
    from pyvis.network import Network
    import streamlit.components.v1 as components

    G = graph_store.get_graph()
    if len(G.nodes) > 0:
        net = Network(height="600px", width="100%", notebook=False, directed=True)
        # Convert NetworkX to Pyvis
        for n, data in G.nodes(data=True):
            label = data.get('name', n)
            color = "#97c2fc"
            if data.get('type') == 'Scheme': color = "#ffb347"
            elif data.get('type') == 'Ministry': color = "#b19cd9"
            elif data.get('type') == 'District': color = "#77dd77"
            net.add_node(n, label=label, title=str(data), color=color)
        
        for u, v, data in G.edges(data=True):
            net.add_edge(u, v, label=data.get('predicate', ''))
        
        net.save_graph("graph.html")
        HtmlFile = open("graph.html", 'r', encoding='utf-8')
        source_code = HtmlFile.read() 
        components.html(source_code, height=600)
    else:
        st.info("No nodes in the graph yet. Ingest some data to build the ontology.")
