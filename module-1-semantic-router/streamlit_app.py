import streamlit as st
import json
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.append(str(APP_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from router import RouteLayer

st.set_page_config(
    page_title="Module 1 Semantic Router",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.title("Semantic Receipt Router")
st.caption("Route simple receipts to cheaper models and complex receipts to stronger reasoning models.")

# Cache the router instance so it's not recreated on every Streamlit rerun
@st.cache_resource
def get_router():
    return RouteLayer()

router = get_router()

receipt_text = st.text_area(
    "Paste your receipt text below:",
    height=200,
    placeholder=""
)

if st.button("Route & Extract", type="primary"):
    if not receipt_text.strip():
        st.warning("Please enter some receipt text first.")
    else:
        with st.spinner("Processing..."):
            try:
                result = router.handle(receipt_text)
                
                # Display Results
                st.success("Processing Complete!")
                
                col1, col2 = st.columns(2)
                with col1:
                    intent_display = result["intent"].replace("_", " ").title()
                    st.metric(label="Intent Classified", value=intent_display)
                with col2:
                    st.metric(label="Model Route", value=result["model_used"])
                
                st.subheader("Extracted Data")
                st.json(result["data"])
                
            except Exception as e:
                import traceback
                st.error(f"Error Processing Receipt: {str(e)}")
                with st.expander("Show Detailed Error Trace"):
                    st.text(traceback.format_exc())
