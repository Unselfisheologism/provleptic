import streamlit as st
import os
import pandas as pd
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
from src.rules.engine import RuleEngine
from src.rules.sample_rules import pmay_review, health_coverage, agriculture_credit
from src.auth.simulator import RoleSimulator, can_export, can_view_audit, can_flag_for_review
from src.audit.logger import AuditLogger
from src.recommendation.generator import RecommendationGenerator
from src.compliance.dpdp import DPDPChecker, Purpose
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
    rule_engine = RuleEngine("src/rules/sample_rules")
    audit_logger = AuditLogger()
    recommendation_generator = RecommendationGenerator()
    dpdp_checker = DPDPChecker()
    return {
        "csv_loader": csv_loader,
        "pdf_loader": pdf_loader,
        "vector_store": vector_store,
        "metadata_store": metadata_store,
        "retriever": retriever,
        "generator": generator,
        "ontology_extractor": ontology_extractor,
        "graph_store": graph_store,
        "query_translator": query_translator,
        "lineage_tracker": lineage_tracker,
        "rule_engine": rule_engine,
        "audit_logger": audit_logger,
        "recommendation_generator": recommendation_generator,
        "dpdp_checker": dpdp_checker,
    }

services = get_services()

st.set_page_config(page_title="Indian Public Data RAG", page_icon="🇮🇳")

st.title("🇮🇳 Sovereign RAG for Indian Public Data")
st.markdown("""
This tool allows you to query Indian public datasets (CSV/PDF) using natural language.
All processing is local-first, with citations to exact source rows/pages.
""")

# Role simulation
with st.sidebar:
    st.header("👤 Role Simulation")
    role_options = ["analyst", "field_officer", "policymaker"]
    user_role = st.selectbox("Select Role", role_options, index=0)
    
    if "user_role" not in st.session_state:
        st.session_state.user_role = user_role
    else:
        st.session_state.user_role = user_role
    
    st.caption(f"Current: {user_role.title()}")
    
    if user_role == "analyst":
        st.info("📋 View-only access")
    elif user_role == "field_officer":
        st.info("📋 View + Flag + Recommend")
    elif user_role == "policymaker":
        st.info("📋 Full Access + Export")
    
    st.divider()
    st.header("Data Ingestion")
    uploaded_file = st.file_uploader("Upload a CSV or PDF file", type=["csv", "pdf"])
    source_url = st.text_input("Source URL (optional)", value="local")
    
    if st.button("Process & Ingest"):
        if uploaded_file:
            raw_path = os.path.join("data/raw", uploaded_file.name)
            os.makedirs("data/raw", exist_ok=True)
            with open(raw_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            with st.spinner("Processing..."):
                if uploaded_file.name.endswith(".csv"):
                    chunks = services["csv_loader"].load(raw_path, source_url)
                else:
                    chunks = services["pdf_loader"].load(raw_path, source_url)
                
                services["vector_store"].add_documents(chunks)
                
                with st.spinner("Building Ontology Graph..."):
                    for chunk in chunks:
                        chunk_id = f"{chunk['metadata']['content_hash']}_{chunk['metadata']['chunk_index']}"
                        extraction = services["ontology_extractor"].extract(chunk['content'], chunk_id)
                        for node in extraction.nodes:
                            services["graph_store"].add_node(node)
                        for edge in extraction.edges:
                            services["graph_store"].add_edge(edge)
                
                if chunks:
                    meta = chunks[0]['metadata']
                    services["metadata_store"].log_ingestion(
                        file_name=uploaded_file.name,
                        source_url=source_url,
                        ingested_at=meta['ingested_at'],
                        content_hash=meta['content_hash']
                    )
                
                st.success(f"Ingested {len(chunks)} chunks from {uploaded_file.name}")
        else:
            st.error("Please upload a file first.")

    st.header("Ingested Data")
    ingestions = services["metadata_store"].get_all_ingestions()
    for ing in ingestions:
        st.text(f"📄 {ing[1]}")

# Tabs based on role
st.header("Interactions")
available_tabs = ["🔍 Q&A", "🕸️ Ontology Query", "📊 Visualize", "⚡ Rule Engine", "📋 Audit Log"]
if can_export(user_role):
    available_tabs.append("📥 Export")

selected_tabs = st.tabs(available_tabs)

with selected_tabs[0]:
    question = st.text_input("e.g., Which district in Maharashtra had highest PMAY fund utilization?")
    
    if st.button("Query"):
        if question:
            with st.spinner("Searching and generating answer..."):
                context_chunks = services["retriever"].retrieve(question)
                if not context_chunks:
                    st.warning("No relevant data found. Please ingest some data first.")
                else:
                    result = services["generator"].generate_answer(question, context_chunks)
                    
                    st.markdown("### Answer")
                    st.write(result['answer'])
                    
                    st.markdown(f"**Confidence Score:** {result['confidence_score']:.2f}")
                    
                    # Log to audit
                    services["audit_logger"].log(
                        role=user_role,
                        action="query",
                        query=question,
                        result=result,
                        metadata={"confidence": result['confidence_score']}
                    )
                    
                    with st.expander("Sources & Context"):
                        for i, chunk in enumerate(context_chunks):
                            st.markdown(f"**Source {i+1}**")
                            st.json(chunk['metadata'])
                            st.text(chunk['content'])
        else:
            st.error("Please enter a question.")

with selected_tabs[1]:
    ont_query = st.text_input("Ask about relationships (e.g., Show schemes for farmers in Maharashtra)")
    if st.button("Search Graph"):
        if ont_query:
            with st.spinner("Querying graph..."):
                results = services["query_translator"].query(ont_query)
                for res in results:
                    with st.expander(f"Entity: {res.get('name', res['id'])}"):
                        st.json(res)
                        if "source_chunk_id" in res:
                            lineage = services["lineage_tracker"].get_source_details(res["source_chunk_id"])
                            st.markdown("**Lineage Info:**")
                            st.json(lineage)
        else:
            st.error("Please enter a graph query.")

with selected_tabs[2]:
    st.markdown("### Interactive Ontology Graph")
    from pyvis.network import Network
    import streamlit.components.v1 as components

    G = services["graph_store"].get_graph()
    if len(G.nodes) > 0:
        net = Network(height="600px", width="100%", notebook=False, directed=True)
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

with selected_tabs[3]:
    st.markdown("### ⚡ Policy Rule Engine")
    st.markdown("Evaluate YAML-defined rules against district data")
    
    # Sample data input
    st.subheader("Test Data")
    col1, col2 = st.columns(2)
    with col1:
        district_name = st.text_input("District Name", value="Nashik")
        pmay_util = st.slider("PMAY Utilization %", 0, 100, 45)
        population = st.number_input("Population", value=6000000)
    with col2:
        health_coverage = st.slider("Health Coverage %", 0, 100, 55)
        kcc_disbursement = st.slider("KCC Disbursement %", 0, 100, 65)
        agrarian = st.slider("Agrarian %", 0, 100, 60)
    
    context = {
        "District": {
            "name": district_name,
            "pmay_utilization_percent": pmay_util,
            "population": population,
            "health_scheme_coverage_percent": health_coverage,
            "kcc_disbursement_percent": kcc_disbursement,
            "agrarian_percentage": agrarian,
        },
        "entity_type": "District",
        "identifier": district_name
    }
    
    if st.button("Evaluate Rules"):
        with st.spinner("Evaluating rules..."):
            results = services["rule_engine"].evaluate(context)
            
            # Log to audit
            services["audit_logger"].log(
                role=user_role,
                action="rule_evaluation",
                query=f"Evaluate rules for {district_name}",
                result={"rules_triggered": sum(1 for r in results if r.triggered)},
                metadata={"district": district_name, "rule_count": len(results)}
            )
            
            triggered = [r for r in results if r.triggered]
            non_triggered = [r for r in results if not r.triggered]
            
            if triggered:
                st.success(f"🚨 {len(triggered)} rule(s) triggered!")
                for r in triggered:
                    with st.expander(f"🚨 {r.rule_id} - {r.priority.upper()} PRIORITY"):
                        st.markdown(f"**Description:** {r.description}")
                        st.markdown(f"**Action:** {r.action_result}")
                        
                        if r.recommendation_prompt and can_flag_for_review(user_role):
                            st.markdown("**Generating Recommendation...**")
                            recommendation = services["recommendation_generator"].generate(
                                rule_id=r.rule_id,
                                rule_prompt=r.recommendation_prompt,
                                context_data=context["District"],
                                district_name=district_name
                            )
                            
                            st.markdown("### 📋 Recommendation")
                            st.markdown(recommendation.summary)
                            
                            for i, rec in enumerate(recommendation.recommendations):
                                with st.expander(f"Recommendation {i+1}: {rec.title}"):
                                    st.markdown(f"**Steps:**")
                                    for step in rec.steps:
                                        st.markdown(f"- {step}")
                                    st.markdown(f"**Outcome:** {rec.outcome}")
                                    st.markdown(f"**Citation:** {rec.citation}")
                                    st.markdown(f"**Confidence:** {rec.confidence:.0%}")
            else:
                st.info("No rules triggered for this data.")
            
            with st.expander("Show All Rules"):
                st.markdown(f"**Total Rules:** {len(results)}")
                for r in non_triggered:
                    st.text(f"✓ {r.rule_id} - not triggered")

with selected_tabs[4]:
    st.markdown("### 📋 Audit Log")
    st.markdown("Immutable audit trail with hash chain verification")
    
    entries = services["audit_logger"].get_entries(limit=50)
    st.markdown(f"**Total Entries:** {len(entries)}")
    
    # Chain verification
    if st.button("Verify Hash Chain"):
        verification = services["audit_logger"].verify_chain_integrity()
        if verification["valid"]:
            st.success(f"✅ {verification['message']}")
        else:
            st.error(f"❌ {verification['message']}")
    
    # Show entries
    for entry in entries[:10]:
        with st.expander(f"#{entry['id']} - {entry['action']} by {entry['user_role']}"):
            st.json({
                "id": entry["id"],
                "action": entry["action"],
                "user_role": entry["user_role"],
                "query_hash": entry["query_hash"][:16] + "...",
                "timestamp": entry["timestamp"],
                "metadata": entry.get("metadata_parsed", {})
            })
    
    if can_view_audit(user_role):
        st.divider()
        st.markdown("### DPDP Compliance Check")
        
        # Sample compliance check
        sample_data = {
            "name": district_name,
            "pmay_utilization_percent": pmay_util,
            "population": population
        }
        
        minimized = services["dpdp_checker"].minimize_data(
            sample_data,
            Purpose.DISTRICT_REVIEW,
            data_id=f"sample_{district_name}"
        )
        
        st.markdown("**Data Minimization Applied:**")
        st.json(minimized)

# Export tab (only for policymaker/admin)
if can_export(user_role) and len(selected_tabs) > 5:
    with selected_tabs[5]:
        st.markdown("### 📥 Export Report")
        st.info("Export functionality enabled for your role")
        
        if st.button("Generate CSV Report"):
            # Sample data export
            data = {
                "District": ["Nashik", "Pune", "Mumbai"],
                "PMAY_Utilization": [45, 78, 62],
                "Population": [6000000, 9500000, 12500000]
            }
            df = pd.DataFrame(data)
            csv = df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                csv,
                "policy_report.csv",
                "text/csv"
            )