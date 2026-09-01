from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

import streamlit as st

from app import LLMError, PDFParseError, SegmentationError, VideoRenderError, VidtsError
from app.config import AppConfig, load_config, load_env_file
from app.pipeline import Pipeline, PipelineResult

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_env_file(PROJECT_ROOT / ".env")
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
SUPPORTED_VOICES = [
    "en-US-BrianNeural",
    "en-US-AriaNeural",
    "en-US-GuyNeural",
    "en-GB-SoniaNeural",
]
SUPPORTED_MODELS = [
    "groq/compound-mini",
]
PIPELINE_STAGES = [
    ("Ingest", "Extracting pages and rendering images"),
    ("Analysis", "Analyzing document structure and content density"),
    ("Recap", "Generating narration script via LLM"),
    ("Segmentation", "Calculating pacing and scene segment mapping"),
    ("Narration", "Synthesizing voiceover audio clips"),
    ("Video", "Assembling scenes and rendering MP4 video"),
]


def inject_styles(theme_mode: str) -> None:
    """Apply a complete light or dark design-token system to every Streamlit surface."""
    tokens = (
        """
        :root {
          --canvas: #181715; --surface: #24221f; --surface-raised: #2b2824; --ink: #f5efe5;
          --muted: #c6bdb2; --soft: #968c82; --line: #4b443c; --accent: #f0644c;
          --accent-strong: #ff866e; --accent-wash: #3c2924; --positive: #bdd0ad;
          --positive-wash: #2b3528; --sidebar: #11110f; --sidebar-2: #191816;
          --side-ink: #f5efe5; --side-muted: #a9a097; --shadow: rgba(0,0,0,.27);
        }
        """
        if theme_mode == "Dark studio"
        else """
        :root {
          --canvas: #f7f4ee; --surface: #fcfaf6; --surface-raised: #eee8de; --ink: #28231f;
          --muted: #675f56; --soft: #8f857a; --line: #d6ccc0; --accent: #e54b33;
          --accent-strong: #c9402b; --accent-wash: #fbe6df; --positive: #52664a;
          --positive-wash: #e4ebdf; --sidebar: #22201d; --sidebar-2: #1a1917;
          --side-ink: #f8f4ec; --side-muted: #aaa197; --shadow: rgba(70,53,34,.10);
        }
        """
    )
    styles = """
    <style>
      THEME_TOKENS
      html, body, [data-testid="stAppViewContainer"], .stApp { background: var(--canvas) !important; color: var(--ink) !important; }
      [data-testid="stAppViewContainer"] .main { background: var(--canvas) !important; }
      [data-testid="stHeader"] { background: transparent !important; }
      [data-testid="stHeader"] * { color: var(--soft) !important; }
      [data-testid="stAppViewContainer"] .main .block-container { max-width: 1210px; padding-top: 3.25rem; padding-bottom: 4.75rem; }
      [data-testid="stAppViewContainer"] p, [data-testid="stAppViewContainer"] label, [data-testid="stAppViewContainer"] li { color: var(--muted); }
      [data-testid="stAppViewContainer"] h1, [data-testid="stAppViewContainer"] h2, [data-testid="stAppViewContainer"] h3 { color: var(--ink); }
      [data-testid="stDivider"] { border-color: var(--line); }
      [data-testid="stSidebar"] { background: var(--sidebar) !important; border-right: 1px solid var(--line); }
      [data-testid="stSidebar"] > div:first-child { background: linear-gradient(180deg, var(--sidebar) 0%, var(--sidebar-2) 100%) !important; }
      [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: .55rem; }
      .studio-identity { display: flex; align-items: center; gap: .7rem; margin: .2rem 0 .6rem; }
      .sidebar-mark { display: grid; place-items: center; width: 2.35rem; height: 2.35rem; color: #fff !important; background: var(--accent); border-radius: .28rem; font-family: Georgia, serif; font-size: 1.25rem; font-weight: 700; box-shadow: 4px 4px 0 rgba(255,255,255,.08); }
      .studio-identity-copy { display: grid; gap: .08rem; }
      .studio-identity-copy strong { color: var(--side-ink) !important; font-family: Georgia, serif; font-size: 1.2rem; font-weight: 400; letter-spacing: -.04em; }
      .studio-identity-copy span, .sidebar-eyebrow { color: var(--side-muted) !important; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .62rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
      .sidebar-section { margin: 1.1rem 0 .15rem; color: var(--side-muted) !important; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .64rem; font-weight: 700; letter-spacing: .11em; }
      .sidebar-footnote { margin: .65rem 0 0; padding: .8rem .85rem; color: var(--side-muted) !important; background: rgba(255,255,255,.04); border-left: 2px solid var(--accent); font-size: .72rem; line-height: 1.55; }
      [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: var(--side-muted) !important; font-size: .72rem; line-height: 1.5; }
      [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { color: var(--side-ink) !important; font-size: .72rem; font-weight: 700; }
      [data-testid="stSidebar"] [data-testid="stExpander"] { border: 1px solid rgba(255,255,255,.14); border-radius: .35rem; background: rgba(255,255,255,.035); }
      [data-testid="stSidebar"] [data-testid="stExpander"] summary { color: var(--side-ink) !important; font-size: .78rem; font-weight: 800; letter-spacing: .015em; }
      [data-testid="stSidebar"] input, [data-testid="stSidebar"] [data-baseweb="select"] > div, [data-testid="stSidebar"] [data-baseweb="input"] > div { color: var(--side-ink) !important; background: rgba(255,255,255,.075) !important; border-color: rgba(255,255,255,.15) !important; }
      [data-testid="stSidebar"] [data-baseweb="select"] *, [data-testid="stSidebar"] [data-baseweb="input"] * { color: var(--side-ink) !important; }
      [data-testid="stSidebar"] [data-testid="stRadio"] > div { gap: 0; padding: .22rem; background: rgba(255,255,255,.07); border-radius: .35rem; }
      [data-testid="stSidebar"] [data-testid="stRadio"] label { margin: 0; padding: .36rem .4rem; border-radius: .23rem; color: var(--side-muted) !important; font-size: .7rem; }
      [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) { color: #fff !important; background: var(--accent); }
      [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) * { color: #fff !important; }
      [data-testid="stSidebar"] [data-baseweb="slider"] div[role="slider"] { background: var(--accent); border-color: var(--accent); }
      [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.11); }
      .vidts-hero { position: relative; display: grid; grid-template-columns: minmax(0, 1.14fr) minmax(238px, .46fr); gap: 4.25rem; align-items: end; margin: -.3rem 0 2.35rem; padding: 0 0 2.55rem; border-bottom: 1px solid var(--line); }
      .vidts-hero::after { content: ""; position: absolute; bottom: -1px; left: 0; width: 112px; height: 3px; background: var(--accent); }
      .vidts-index, .vidts-section-label { display: flex; align-items: center; justify-content: space-between; gap: .75rem; color: var(--accent-strong); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .66rem; font-weight: 700; letter-spacing: .11em; }
      .vidts-hero h1 { max-width: 690px; margin: .9rem 0 1.1rem; color: var(--ink); font-family: Georgia, serif; font-size: clamp(3rem, 5.35vw, 5.35rem); font-weight: 400; letter-spacing: -.065em; line-height: .9; }
      .vidts-hero p { max-width: 620px; margin: 0; color: var(--muted); font-size: 1.08rem; line-height: 1.65; }
      .vidts-hero-note { position: relative; padding: 1.32rem 0 1.25rem 1.35rem; border-left: 1px solid var(--line); }
      .vidts-hero-note::before { content: ""; position: absolute; top: 0; left: -3px; width: 5px; height: 5px; border-radius: 50%; background: var(--accent); }
      .vidts-hero-note strong { display: block; margin-bottom: .52rem; color: var(--ink); font-size: .94rem; }
      .vidts-hero-note span { display: block; color: var(--muted); font-size: .81rem; line-height: 1.6; }
      .vidts-workflow-chip { display: inline-flex; align-items: center; gap: .45rem; margin-top: 1.45rem; padding: .42rem .68rem; color: var(--positive); background: var(--positive-wash); border-radius: .25rem; font-size: .72rem; font-weight: 800; }
      .vidts-source-head { display: flex; align-items: end; justify-content: space-between; gap: 1rem; margin: 0 0 .72rem; }
      .vidts-source-head h3 { margin: .32rem 0 0; color: var(--ink); font-family: Georgia, serif; font-size: 1.78rem; font-weight: 400; letter-spacing: -.04em; }
      .vidts-source-head p { margin: 0 0 .1rem; color: var(--soft); font-size: .79rem; text-align: right; }
      [data-testid="stFileUploader"] { position: relative; padding: 0; overflow: hidden; background: var(--surface); border: 1px solid var(--line); border-radius: .32rem; box-shadow: 7px 7px 0 var(--surface-raised); }
      [data-testid="stFileUploader"]::before { content: ""; position: absolute; z-index: 2; top: 0; bottom: 0; left: 0; width: 3px; background: var(--accent); }
      [data-testid="stFileUploaderDropzone"] { min-height: 195px; padding: 2.25rem 1.25rem !important; background: repeating-linear-gradient(0deg, transparent 0 33px, color-mix(in srgb, var(--line) 34%, transparent) 33px 34px), linear-gradient(90deg, transparent 0 25px, color-mix(in srgb, var(--accent) 12%, transparent) 25px 26px, transparent 26px) !important; border: 0 !important; border-radius: 0 !important; }
      [data-testid="stFileUploaderDropzone"] * { color: var(--muted) !important; }
      [data-testid="stFileUploaderDropzone"] button { color: var(--accent-strong) !important; background: var(--accent-wash) !important; border: 1px solid color-mix(in srgb, var(--accent) 45%, var(--line)) !important; border-radius: .22rem !important; font-weight: 800 !important; }
      .upload-note { color: var(--soft) !important; font-size: .8rem; margin-top: -.25rem; }
      div.stButton > button[kind="primary"] { min-height: 2.9rem; padding-inline: 1.35rem; color: #fff !important; background: var(--accent); border: 0; border-radius: .28rem; box-shadow: 0 8px 20px color-mix(in srgb, var(--accent) 25%, transparent); font-size: .9rem; font-weight: 800; letter-spacing: .01em; transition: transform .16s ease, background .16s ease; }
      div.stButton > button[kind="primary"]:hover { color: #fff !important; background: var(--accent-strong); transform: translateY(-1px); }
      div.stButton > button[kind="primary"]:active { transform: scale(.98); }
      [data-testid="stStatusWidget"] { border: 1px solid var(--line); border-left: 3px solid var(--accent); border-radius: .35rem; background: var(--surface); box-shadow: 0 13px 28px var(--shadow); }
      [data-testid="stStatusWidget"] summary, [data-testid="stStatusWidget"] * { color: var(--ink); }
      [data-testid="stStatusWidget"] summary { font-family: Georgia, serif; font-size: 1.06rem; }
      [data-testid="stProgressBar"] > div > div > div { background: var(--accent); }
      [data-baseweb="tab-list"] { gap: 1.45rem; border-bottom: 1px solid var(--line); }
      [data-baseweb="tab"] { height: 2.8rem; padding: 0; color: var(--soft); font-size: .81rem; font-weight: 800; }
      [data-baseweb="tab"][aria-selected="true"] { color: var(--accent-strong); }
      [data-baseweb="tab-highlight"] { height: 2px; background: var(--accent); }
      .vidts-results-head { display: flex; align-items: end; justify-content: space-between; gap: 1rem; margin: 3.15rem 0 1.1rem; }
      .vidts-results-head h2 { margin: .38rem 0 0; color: var(--ink); font-family: Georgia, serif; font-size: 2.35rem; font-weight: 400; letter-spacing: -.055em; }
      .vidts-results-head span { padding: .42rem .58rem; color: var(--positive); background: var(--positive-wash); border-radius: .22rem; font-size: .7rem; font-weight: 800; white-space: nowrap; }
      .result-meta { margin-bottom: 1.45rem; padding: .95rem 1rem; color: var(--muted); background: var(--surface-raised); border-left: 3px solid var(--accent); font-size: .84rem; }
      .result-meta strong { color: var(--ink); }
      [data-testid="stImage"] img, [data-testid="stVideo"] video { border: 1px solid var(--line); border-radius: .35rem; box-shadow: 0 12px 25px var(--shadow); }
      [data-testid="stAlert"] { color: var(--ink); background: var(--surface-raised); border-color: var(--line); }
      @media (max-width: 800px) { .vidts-hero { grid-template-columns: 1fr; gap: 1.7rem; padding-bottom: 1.9rem; } .vidts-hero h1 { font-size: clamp(2.75rem, 13vw, 4rem); } .vidts-hero-note { max-width: 28rem; } .vidts-source-head, .vidts-results-head { align-items: start; flex-direction: column; } .vidts-source-head p { text-align: left; } }
    </style>
    """
    st.markdown(styles.replace("THEME_TOKENS", tokens), unsafe_allow_html=True)


def _option_index(options: list[str], selected: str) -> int:
    return options.index(selected) if selected in options else 0


def render_sidebar(defaults: AppConfig) -> dict[str, Any]:
    """Render controls and return a serializable set of in-memory runtime overrides."""
    with st.sidebar:
        st.markdown(
            "<div class='studio-identity'><span class='sidebar-mark'>V</span><span class='studio-identity-copy'>"
            "<strong>vidts studio</strong><span>DOCUMENT → FIRST CUT</span></span></div>",
            unsafe_allow_html=True,
        )
        st.caption("A focused production desk for this generation.")
        st.markdown("<p class='sidebar-section'>APPEARANCE</p>", unsafe_allow_html=True)
        st.radio(
            "Studio appearance",
            options=["Light desk", "Dark studio"],
            key="vidts_theme",
            horizontal=True,
            label_visibility="collapsed",
        )
        st.divider()

        st.markdown("<p class='sidebar-section'>GENERATION CONTROLS</p>", unsafe_allow_html=True)
        with st.expander("Language model", expanded=True):
            model_options = list(SUPPORTED_MODELS)
            preferred_model = defaults.llm.model if defaults.llm.model in model_options else model_options[0]
            if "vidts_model" not in st.session_state:
                st.session_state["vidts_model"] = preferred_model
            model = st.selectbox(
                "Model",
                model_options,
                index=_option_index(model_options, preferred_model),
                key="vidts_model",
            )

        with st.expander("Narration voice", expanded=True):
            voice_options = list(SUPPORTED_VOICES)
            if defaults.narration.voice not in voice_options:
                voice_options.insert(0, defaults.narration.voice)
            voice = st.selectbox("Edge-TTS voice", voice_options, index=_option_index(voice_options, defaults.narration.voice))
            initial_rate = int(defaults.narration.rate.replace("%", "").replace("+", "") or "0")
            rate = st.slider("Speech rate", min_value=-50, max_value=50, value=initial_rate, step=5, format="%d%%")

        with st.expander("Video output", expanded=True):
            resolution_options = ["1920x1080", "1280x720", "1080x1080"]
            resolution = st.selectbox(
                "Resolution",
                resolution_options,
                index=_option_index(resolution_options, defaults.video.resolution),
            )
            fps = st.select_slider("FPS", options=[24, 30, 60], value=defaults.video.fps if defaults.video.fps in [24, 30, 60] else 30)

        with st.expander("Processing limits", expanded=True):
            default_pages = defaults.document.max_pages or 10
            max_pages = st.slider("Maximum PDF pages", min_value=1, max_value=20, value=min(max(default_pages, 1), 20))

        st.markdown(
            "<p class='sidebar-footnote'><span class='sidebar-eyebrow'>Guest session</span><br>"
            "These controls change only the current generation. Your project defaults stay untouched.</p>",
            unsafe_allow_html=True,
        )

    return {
        "model": model,
        "voice": voice,
        "rate": f"{rate:+d}%",
        "resolution": resolution,
        "fps": int(fps),
        "max_pages": int(max_pages),
    }


def build_runtime_config(defaults: AppConfig, settings: dict[str, Any], run_directory: Path) -> AppConfig:
    """Create a per-run config entirely in memory; config.yaml is never rewritten."""
    return replace(
        defaults,
        llm=replace(
            defaults.llm,
            model=settings["model"],
        ),
        narration=replace(defaults.narration, engine="edge-tts", voice=settings["voice"], rate=settings["rate"]),
        video=replace(defaults.video, resolution=settings["resolution"], fps=settings["fps"]),
        document=replace(defaults.document, max_pages=settings["max_pages"]),
        output=replace(defaults.output, directory=str(run_directory)),
    )


def save_uploaded_pdf(uploaded_file: Any, run_directory: Path) -> Path:
    """Save the temporary user upload inside the run folder for the existing pipeline."""
    if not uploaded_file.name.lower().endswith(".pdf"):
        raise PDFParseError("Only PDF files can be processed.")
    source_directory = run_directory / "source"
    source_directory.mkdir(parents=True, exist_ok=True)
    target = source_directory / "source.pdf"
    target.write_bytes(uploaded_file.getvalue())
    if target.stat().st_size == 0:
        raise PDFParseError("The uploaded PDF is empty.")
    return target


def existing_file(path: Path | None) -> Path | None:
    return path if path and path.exists() and path.is_file() else None


def final_video_path(result: PipelineResult) -> Path | None:
    """Find a playable final MP4, including the first part when a combined file is unavailable."""
    direct = existing_file(result.video.video_path)
    if direct:
        return direct
    for part in result.video.parts:
        candidate = existing_file(part.video_path)
        if candidate:
            return candidate
    return None


def render_results(result: PipelineResult) -> None:
    """Render pipeline artifacts in focused, inspectable tabs."""
    st.markdown(
        "<div class='vidts-results-head'><div><div class='vidts-section-label'>OUTPUT / FIRST CUT</div>"
        "<h2>Your story is ready to review.</h2></div><span>RENDER COMPLETE</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='result-meta'><strong>{result.document.title}</strong> · {len(result.document.pages)} page(s) · "
        f"{len(result.recap.scenes)} scene(s) · {result.video.resolution} at {result.video.fps} FPS</div>",
        unsafe_allow_html=True,
    )
    video_tab, script_tab, pages_tab, audio_tab = st.tabs(
        ["Final video", "Narration script", "Extracted pages", "Audio clips"]
    )

    with video_tab:
        video_path = final_video_path(result)
        if video_path:
            video_bytes = video_path.read_bytes()
            st.video(video_bytes, format="video/mp4")
            st.download_button(
                "Download MP4",
                data=video_bytes,
                file_name=f"{result.document.title or 'vidts-recap'}.mp4",
                mime="video/mp4",
                type="primary",
            )
        else:
            st.warning("The pipeline completed, but no playable MP4 was found. Check the Video stage output and FFmpeg logs.")

    with script_tab:
        if result.recap.summary:
            st.info(result.recap.summary)
        if result.recap.scenes:
            for scene in result.recap.scenes:
                st.markdown(
                    f"**Scene {scene.scene_index:02d} · Page {scene.page_number} · "
                    f"{scene.estimated_duration_seconds:.1f}s**  \n"
                    f"_{scene.title}_  \n\n{scene.narration_text}"
                )
                st.divider()
        else:
            st.code(result.recap.raw_script or "The LLM did not return a scene-by-scene recap.")

    with pages_tab:
        pages_with_images = [page for page in result.document.pages if existing_file(page.image_path)]
        if not pages_with_images:
            st.warning("No page previews were rendered. The recap can still complete when PDF text extraction succeeds.")
        else:
            for start in range(0, len(pages_with_images), 2):
                columns = st.columns(2)
                for column, page in zip(columns, pages_with_images[start : start + 2], strict=False):
                    with column:
                        st.image(str(page.image_path), caption=f"Page {page.page_number}", use_container_width=True)

    with audio_tab:
        if not result.narration.tracks:
            st.warning("No audio tracks were returned. This can happen when Edge-TTS is unavailable.")
        for track in result.narration.tracks:
            st.markdown(f"#### Part {track.segment_part_number} narration")
            master_audio = existing_file(track.audio_path)
            if master_audio:
                st.audio(master_audio.read_bytes(), format=f"audio/{track.audio_format}")
            for scene_audio in track.scenes:
                clip = existing_file(scene_audio.audio_path)
                if clip:
                    st.caption(f"Scene {scene_audio.scene_index} · Page {scene_audio.page_number} · {scene_audio.duration_seconds:.1f}s")
                    st.audio(clip.read_bytes(), format="audio/mp3")


def explain_error(error: Exception, settings: dict[str, Any]) -> str:
    if isinstance(error, PDFParseError):
        return "We could not read that file as a valid PDF. Try exporting it again and upload the new PDF."
    if isinstance(error, LLMError):
        return f"Language model error: {error}"
    if isinstance(error, VideoRenderError):
        return "The document and narration were created, but the MP4 render failed. Confirm that FFmpeg is installed and available on PATH."
    if isinstance(error, SegmentationError):
        return "The generated recap could not be safely split into scenes. Try a shorter PDF or reduce the maximum page count."
    error_text = str(error).lower()
    if "edge" in error_text or "tts" in error_text or "speech" in error_text:
        return "Edge-TTS could not create the narration audio. Check your internet connection and try a different voice."
    return f"The generation stopped unexpectedly: {error}"


def generate_video(uploaded_file: Any, defaults: AppConfig, settings: dict[str, Any]) -> PipelineResult | None:
    run_directory = PROJECT_ROOT / "output" / "streamlit" / uuid4().hex
    runtime_config = build_runtime_config(defaults, settings, run_directory)
    try:
        pdf_path = save_uploaded_pdf(uploaded_file, run_directory)
        pipeline = Pipeline.from_config(runtime_config)
        with st.status("Preparing your document for the first cut…", expanded=True) as status:
            progress = st.progress(0, text="Waiting to begin")

            def report_stage(stage_number: int, stage_name: str, stage_message: str) -> None:
                progress_value = int((stage_number - 1) / len(PIPELINE_STAGES) * 100)
                label = f"{stage_number}/6 {stage_name}: {stage_message}"
                status.update(label=label, state="running", expanded=True)
                progress.progress(progress_value, text=label)

            result = pipeline.run(pdf_path, progress_callback=report_stage)
            progress.progress(100, text="6/6 Video: MP4 video ready")
            status.update(label="Your first cut is ready.", state="complete", expanded=False)
        return result
    except (PDFParseError, LLMError, SegmentationError, VideoRenderError, VidtsError) as error:
        st.error(explain_error(error, settings))
    except Exception as error:  # A UI boundary keeps TTS/network and unexpected errors readable.
        st.error(explain_error(error, settings))
    return None


def main() -> None:
    """Render the Streamlit application."""
    st.set_page_config(page_title="vidts — PDF to narrated video", page_icon="▶", layout="wide")
    inject_styles(st.session_state.get("vidts_theme", "Light desk"))
    defaults = load_config(CONFIG_PATH)
    settings = render_sidebar(defaults)

    st.markdown(
        """
        <section class="vidts-hero">
          <div>
            <div class="vidts-index"><span>VIDEO INTELLIGENT DOCUMENT-TO-STORY</span><span>01 / 06</span></div>
            <h1>Give a PDF a voice, pace, and a first cut.</h1>
            <p>Set down a document. vidts extracts the pages, finds the narrative thread, gives it a voice, and makes it ready to watch.</p>
            <span class="vidts-workflow-chip">6 EDITORIAL STAGES · PDF → SCRIPT → NARRATION → VIDEO</span>
          </div>
          <aside class="vidts-hero-note">
            <strong>From source to screen</strong>
            <span>Ingest the document, inspect its structure, shape the recap, then render a narrated MP4.</span>
            <span style="margin-top:.75rem; color:#c9402b; font-family:ui-monospace,monospace; font-size:.68rem; letter-spacing:.08em;">RUNTIME SETTINGS STAY LOCAL TO THIS RUN</span>
          </aside>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='vidts-source-head'><div><div class='vidts-section-label'>SOURCE / DOCUMENT 01</div>"
        "<h3>Set your PDF on the desk.</h3></div><p>PDF only · page limit set in studio controls</p></div>",
        unsafe_allow_html=True,
    )
    uploaded_file = st.file_uploader("Set your PDF on the desk", type=["pdf"], help="PDF only. The processing limit is set in the sidebar.")
    st.markdown("<p class='upload-note'>The uploaded file is stored only in its generation output folder, alongside the preview images, audio clips, and MP4.</p>", unsafe_allow_html=True)

    generate_clicked = st.button("Generate video", type="primary", disabled=uploaded_file is None, use_container_width=False)
    if generate_clicked and uploaded_file:
        result = generate_video(uploaded_file, defaults, settings)
        if result:
            st.session_state["vidts_result"] = result

    result = st.session_state.get("vidts_result")
    if result:
        st.divider()
        render_results(result)


if __name__ == "__main__":
    main()
