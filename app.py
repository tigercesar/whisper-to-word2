import io
import os
import tempfile
import streamlit as st
import whisper
from docx import Document

st.set_page_config(page_title="MP3 to Word Converter", page_icon="🎙️")

st.title("🎙️ MP3 to Word Script Extractor")
st.write("Upload an MP3 audio file to transcribe or translate it into a downloadable Word (.docx) document.")

@st.cache_resource
def load_whisper_model(model_name: str):
    return whisper.load_model(model_name)

def format_timestamp(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"[{minutes:02d}:{secs:02d}]"

def create_word_doc(segments: list, source_filename: str, include_timestamps: bool) -> bytes:
    doc = Document()
    doc.add_heading("Extracted Audio Script", level=1)
    doc.add_paragraph(f"Source File: {source_filename}")
    doc.add_paragraph("")

    for segment in segments:
        text = segment["text"].strip()
        if not text:
            continue
        if include_timestamps:
            doc.add_paragraph(f"{format_timestamp(segment['start'])} {text}")
        else:
            doc.add_paragraph(text)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

# Sidebar settings
with st.sidebar:
    st.header("Settings")
    model_size = st.selectbox(
        "Whisper Model Size",
        options=["tiny", "base", "small"],
        index=1,
        help="'tiny' and 'base' fit safely within Streamlit Community Cloud free memory limits."
    )
    task_option = st.radio(
        "Task",
        options=["transcribe", "translate"],
        format_func=lambda x: "Transcribe (Keep original language)" if x == "transcribe" else "Translate (Convert audio to English)"
    )
    include_timestamps = st.checkbox("Include [MM:SS] timestamps", value=False)

# Upload button
uploaded_file = st.file_uploader("Upload your MP3 file", type=["mp3"])

# Reset previous results if a new file is uploaded
if uploaded_file is not None:
    if st.session_state.get("last_uploaded_file") != uploaded_file.name:
        st.session_state["last_uploaded_file"] = uploaded_file.name
        st.session_state.pop("docx_bytes", None)
        st.session_state.pop("docx_filename", None)
        st.session_state.pop("transcript_preview", None)

    st.audio(uploaded_file, format="audio/mp3")

    if st.button("Extract Script to Word", type="primary"):
        tmp_path = None
        try:
            with st.spinner(f"Loading Whisper '{model_size}' model..."):
                model = load_whisper_model(model_size)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            with st.spinner("Extracting script from audio (this may take a moment)..."):
                result = model.transcribe(tmp_path, task=task_option)

            docx_bytes = create_word_doc(
                segments=result["segments"],
                source_filename=uploaded_file.name,
                include_timestamps=include_timestamps
            )

            base_name = os.path.splitext(uploaded_file.name)[0]
            st.session_state["docx_bytes"] = docx_bytes
            st.session_state["docx_filename"] = f"{base_name}_script.docx"
            st.session_state["transcript_preview"] = result["text"].strip()

        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

# Preview and download button
if "docx_bytes" in st.session_state:
    st.success("Script extracted successfully!")
    st.text_area("Extracted Script Preview", value=st.session_state["transcript_preview"], height=220)
    st.download_button(
        label="📥 Download Word Document (.docx)",
        data=st.session_state["docx_bytes"],
        file_name=st.session_state["docx_filename"],
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
