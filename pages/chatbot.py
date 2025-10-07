import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
from pages.db_path import db_path


load_dotenv()


@st.cache_resource(show_spinner=False)
def get_openai_client(api_key: str):
    return OpenAI(api_key=api_key)


@st.cache_resource(show_spinner=False)
def get_chroma_collection():
    # Paths mirror admin_panel.py
    base_path = db_path()
    output_dir = os.path.join(base_path, "hazmat_chroma")
    client = chromadb.PersistentClient(path=output_dir)
    collection = client.get_or_create_collection("hazmat_data")
    return collection


EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"

# Exact path variables (for reference/debug parity with admin_panel.py)
PATH = db_path()
OUTPUT_DIR = os.path.join(PATH, "hazmat_chroma")
INDEX_PATH = os.path.join(OUTPUT_DIR, "embeddings_index.json")


def resolve_api_key() -> str:
    # Use environment variables only
    env_key = os.getenv("gpt_api_key") or os.getenv("OPENAI_API_KEY") or ""
    return env_key


def render_sidebar_nav():
    def set_go_back_flag():
        st.session_state["__goto_main_display__"] = True
    st.sidebar.button("Go Back", use_container_width=True, on_click=set_go_back_flag)


def chat_tab(api_key: str):
    st.subheader("Chat")
    client = get_openai_client(api_key)

    HAZMAT_SYSTEM_PROMPT = (
        "You are the assistant for HazMat GIS (hazmat-gis.com). "
        "Provide hazmat-focused answers using your general knowledge when needed (not limited to any database), "
        "covering chemical, biological, radiological, nuclear, and explosive (CBRNE) topics, incident patterns, risk factors, and best-practice considerations. "
        "Data on the site typically includes: Category, Title, Country, City, Date, Casualty, Injuries, Impact, Full Link, and Coordinates. "
        "Always include practical, responsible guidance; avoid medical, legal, or emergency-response advice. "
        "Disclaimer: The information is informational only and may be incomplete; verify with official sources and consult qualified professionals as appropriate."
    )

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "system", "content": HAZMAT_SYSTEM_PROMPT}
        ]

    for m in [m for m in st.session_state.chat_messages if m["role"] != "system"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    prompt = st.chat_input("Ask anything about HazMat (worldwide events, concepts, etc.)…")
    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    resp = client.chat.completions.create(
                        model=CHAT_MODEL,
                        messages=st.session_state.chat_messages,
                    )
                    answer = resp.choices[0].message.content
                except Exception as e:
                    answer = f"Error: {e}"
            st.markdown(answer)
        st.session_state.chat_messages.append({"role": "assistant", "content": answer})


def embeddings_tab(api_key: str):
    st.subheader("Embeddings Search")

    collection = get_chroma_collection()
    client = get_openai_client(api_key)

    with st.form("embeddings_search_form", clear_on_submit=False):
        query = st.text_input("Query", placeholder="e.g., chemical spill in Texas")
        # Fixed Top-K to 3 per request
        top_k = 3
        submitted = st.form_submit_button("Search")

    if submitted and query:
        with st.spinner("Searching embeddings..."):
            try:
                q_embed = client.embeddings.create(model=EMBED_MODEL, input=[query]).data[0].embedding
                results = collection.query(query_embeddings=[q_embed], n_results=int(top_k))
            except Exception as e:
                st.error(f"Embedding search failed: {e}")
                return

        if not results.get("ids") or not results["ids"][0]:
            st.warning("No matches found")
            return

        num = len(results["ids"][0])
        st.caption(f"Found {num} result(s)")

        # Prepare structured sources for display and summarization
        sources = []
        for i in range(num):
            doc = results["documents"][0][i] if "documents" in results else ""
            meta = results["metadatas"][0][i] if "metadatas" in results else {}
            dist = results["distances"][0][i] if "distances" in results else None
            sources.append({
                "rank": i + 1,
                "distance": dist,
                "document": doc,
                "metadata": meta or {}
            })

        # Relevance filtering: prefer incidents whose metadata/doc contains query tokens (e.g., location terms like "Texas")
        tokens = [t.lower() for t in query.split() if len(t) > 3]
        def relevance_score(source):
            m = source.get("metadata", {})
            hay = " ".join([
                str(m.get("Title", "")),
                str(m.get("Category", "")),
                str(m.get("Country", "")),
                str(m.get("City", "")),
                str(source.get("document", "")),
            ]).lower()
            return sum(1 for tok in tokens if tok in hay)

        scored = [(relevance_score(s), s) for s in sources]
        scored.sort(key=lambda x: (x[0], - (x[1]["distance"] or 0.0)), reverse=True)
        filtered_sources = [s for score, s in scored if score > 0]
        # Use relevant ones if any, else fall back to original order
        selected_sources = (filtered_sources or sources)[:3]
        sources = selected_sources

        # Always generate the detailed paragraph answer
        with st.spinner("Generating answer..."):
                # Stable HazMat preface + JSON-like compact context for the LLM
                preface = (
                    "You answer for HazMat GIS (hazmat-gis.com), which aggregates public news on CBRNE incidents. "
                    "Use ONLY the provided Top-K context (up to 3 items). Prefer incidents that match the user's location/topic terms; do NOT include unrelated regions. "
                    "Produce a LONG, detailed markdown response with short section headings. "
                    "Structure as: '## HazMat Incident Overview' (1–3 sentences), '### Incident Details' (FOR EACH INCIDENT: write a dense paragraph in prose — no bullets or lists — covering category, where, when, impact, severity, casualties/injuries, notable response/uncertainty), "
                    "then '### Analysis and Recommendations' (cross-incident patterns, practical considerations), and '### Disclaimer' (informational-use note). "
                    "Target roughly 12–18 sentences overall. Where helpful, naturally reference 1–2 source titles inline and include the source link inline in the paragraph when available (markdown link)."
                )

                # Compact, structured context from Top-K
                compact_items = []
                for s in sources:
                    m = s.get("metadata", {}) if isinstance(s.get("metadata"), dict) else {}
                    compact_items.append({
                        "title": (m.get("Title") or ""),
                        "category": (m.get("Category") or ""),
                        "country": (m.get("Country") or ""),
                        "city": (m.get("City") or ""),
                        "date": (m.get("Date") or ""),
                        "impact": (m.get("Impact") or ""),
                        "severity": (m.get("Severity") or m.get("severity") or ""),
                        "casualty": (m.get("Csuality") if m.get("Csuality") is not None else ""),
                        "injuries": (m.get("Injuries") if m.get("Injuries") is not None else ""),
                        "link": (m.get("Full Link") or m.get("url") or ""),
                    })

                # Trim to avoid overly long prompts
                compact_items = compact_items[:10]
                context_lines = []
                for it in compact_items:
                    context_lines.append(
                        f"- title: {it['title']} | category: {it['category']} | place: {it['city']}, {it['country']} | date: {it['date']} | impact: {it['impact']} | severity: {it['severity']} | casualty: {it['casualty']} | injuries: {it['injuries']} | link: {it['link']}"
                    )
                context_text = "\n".join(context_lines)

                try:
                    resp = client.chat.completions.create(
                        model=CHAT_MODEL,
                        messages=[
                            {"role": "system", "content": preface},
                            {"role": "user", "content": f"Question: {query}\nContext (Top-K):\n{context_text}"},
                        ],
                    )
                    final_answer = resp.choices[0].message.content
                    st.markdown(final_answer)

                    # Sources section removed per request
                except Exception as e:
                    st.error(f"Failed to generate answer: {e}")
            # paragraph-only output; sources list removed per request

def main():
    st.title("Chatbot")

    render_sidebar_nav()

    # Perform navigation outside the callback to avoid no-op rerun issues
    if st.session_state.pop("__goto_main_display__", False):
        st.session_state.page = "main_display"
        st.switch_page("pages/main_display.py")
        return

    api_key = resolve_api_key()
    if not api_key:
        st.warning("OpenAI API key not set. Provide it in the sidebar or set env var 'gpt_api_key'.")
        return

    tabs = st.tabs(["General Chat", "Search Incidents"])
    with tabs[0]:
        chat_tab(api_key)
    with tabs[1]:
        embeddings_tab(api_key)


if __name__ == "__main__":
    main()


