import os
import streamlit as st
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for logger_config
sys.path.append(str(Path(__file__).parents[1]))
from logger_config import get_logger

# Set up logger
logger = get_logger(__name__)

# Add the notebook directory to sys.path to allow imports if needed
sys.path.append(str(Path(__file__).parent))

# Load environment variables from .env file in root directory
load_dotenv()
env = os.environ

OLLAMA_MODEL = env.get("OLLAMA_MODEL")
OLLAMA_VISION_MODEL = env.get("OLLAMA_VISION_MODEL")

def load_extractor(name: str):
    """Dynamically import and instantiate the requested extractor."""
    logger.info(f"Loading extractor: {name}")
    
    if name == "Ollama":
        from receipt_extractor2 import ReceiptExtractorOllama
        # Use both text and vision models
        extractor = ReceiptExtractorOllama(
            model=OLLAMA_MODEL, 
            vision_model=OLLAMA_VISION_MODEL, 
            max_retries=3
        )
        logger.info("Ollama extractor (with vision) loaded successfully")
        return extractor
    else:
        from receipt_extractor2 import ReceiptExtractorOpenAI
        # Use gpt-4o-mini for cost efficiency
        extractor = ReceiptExtractorOpenAI(model="gpt-4o-mini", max_retries=3)
        logger.info("OpenAI extractor loaded successfully")
        return extractor

st.set_page_config(page_title="Module 2 Structured Extraction", layout="centered")
st.title("Receipt Structured Extraction")
st.caption("Convert OCR text or images into reliable structured JSON with configurable extraction backends.")
logger.info("Module 2 Streamlit app started")

tab1, tab2 = st.tabs(["Paste Text", "Upload Image"])

with tab1:
    receipt_text = st.text_area("Receipt OCR Text", height=200, placeholder="Enter receipt text here...", key="text_input")

with tab2:
    uploaded_file = st.file_uploader("Choose a receipt image...", type=["png", "jpg", "jpeg", "webp"], key="image_input")
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Uploaded Receipt", use_container_width=True)

# Engine selection
engine = st.selectbox("Extraction Engine", ["Ollama (Local Vision)", "OpenAI (Cloud)"], index=0)

# Add model info display
if engine == "Ollama (Local Vision)":
    st.info("🤖 Using local Gemma3 + LLaVA models via Ollama (Vision + Text)")
else:
    st.info("🌐 Using OpenAI GPT-4o-mini model (Vision + Text)")

if st.button("Extract", type="primary"):
    try:
        # Map engine names to extractor names
        extractor_name = "Ollama" if engine == "Ollama (Local Vision)" else "OpenAI"
        extractor = load_extractor(extractor_name)
        
        with st.spinner("Extracting structured data..."):
            if uploaded_file:
                logger.info(f"Processing uploaded image: {uploaded_file.name}")
                receipt = extractor.extract_from_image(uploaded_file.getvalue(), mime_type=uploaded_file.type)
                logger.info(f"Image extraction successful: {receipt.model_dump()}")
                st.success("✅ Extraction succeeded!")
                st.json(receipt.model_dump())
            else:
                if not receipt_text.strip():
                    st.error("Please provide receipt text or upload an image.")
                    logger.warning("User attempted extraction without input")
                else:
                    logger.info(f"Processing text input: {receipt_text[:50]}...")
                    receipt = extractor.extract(receipt_text)
                    logger.info(f"Text extraction successful: {receipt.model_dump()}")
                    st.success("✅ Extraction succeeded!")
                    
                    # Display structured results
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Merchant", receipt.merchant)
                        st.metric("Category", receipt.category)
                    with col2:
                        st.metric("Total", f"{receipt.total} {receipt.currency}")
                        if receipt.tax:
                            st.metric("Tax", f"{receipt.tax} {receipt.currency}")
                    
                    st.subheader("Full Structured Data")
                    st.json(receipt.model_dump())
                    
    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}")
        st.error(f"❌ Extraction failed: {str(e)}")
        with st.expander("Show Detailed Error"):
            st.code(str(e))
