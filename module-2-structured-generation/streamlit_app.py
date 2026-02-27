import streamlit as st
import json
from pathlib import Path
import sys

# Add the notebook directory to sys.path to allow imports if needed
sys.path.append(str(Path(__file__).parent))

def load_extractor(name: str):
    """Dynamically import and instantiate the requested extractor.
    The extractor classes are defined in the notebook `module-2-structured-generation.ipynb`.
    When the notebook is executed as a module, the classes become importable from a generated
    Python file named `module_2_structured_generation` (Jupyter converts `-` to `_`).
    To keep things simple, we import the classes directly from that module.
    """
    if name == "Ollama":
        from receipt_extractor import ReceiptExtractorOllama
        return ReceiptExtractorOllama()
    else:
        from receipt_extractor import ReceiptExtractorOpenAI
        return ReceiptExtractorOpenAI()

st.set_page_config(page_title="Module 2 Structured Extraction", layout="centered")
st.title("Receipt Structured Extraction")
st.caption("Convert OCR text or images into reliable structured JSON with configurable extraction backends.")

tab1, tab2 = st.tabs(["Paste Text", "Upload Image"])

with tab1:
    receipt_text = st.text_area("Receipt OCR Text", height=200, placeholder="Enter receipt text here...", key="text_input")

with tab2:
    uploaded_file = st.file_uploader("Choose a receipt image...", type=["png", "jpg", "jpeg", "webp"], key="image_input")
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Uploaded Receipt", use_container_width=True)

# Engine selection
engine = st.selectbox("Extraction Engine", ["Ollama", "OpenAI"], index=1 if uploaded_file else 0)

if uploaded_file and engine == "Ollama":
    st.warning("⚠️ Ollama does not support vision extraction. Switching to OpenAI is recommended for images.")

if st.button("Extract"):
    try:
        extractor = load_extractor(engine)
        
        with st.spinner("Extracting structured data..."):
            if uploaded_file:
                if engine != "OpenAI":
                    st.error("❌ Image extraction is currently only supported via the OpenAI engine.")
                else:
                    receipt = extractor.extract_from_image(uploaded_file.getvalue(), mime_type=uploaded_file.type)
                    st.success("✅ Extraction succeeded!")
                    st.json(receipt.model_dump())
            else:
                if not receipt_text.strip():
                    st.error("Please provide receipt text or upload an image.")
                else:
                    receipt = extractor.extract(receipt_text)
                    st.success("✅ Extraction succeeded!")
                    st.json(receipt.model_dump())
                    
    except Exception as e:
        st.error(f"❌ Extraction failed: {e}")
        if hasattr(e, "__cause__") and e.__cause__:
            st.code(str(e.__cause__))
