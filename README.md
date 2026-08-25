# vidts

**Video Intelligent Document-to-Story**: A local-first Python application that transforms generic PDF documents into engaging, narrated recap/explainer videos.

> **Note**: This repository is currently an **initial architecture skeleton**. Core domain models, interfaces, configuration loaders, Ollama LLM provider abstractions, segmentation rules, and CLI harnesses are implemented and tested. Heavy AI/media generation (e.g. OCR, real-time TTS synthesis, and video rendering) are currently cleanly isolated behind placeholder implementations.

---

## What is vidts?

`vidts` is designed to take unstructured or semi-structured PDF documents and automatically turn them into structured, paced, narrated explainer videos. Unlike chapter-bound comic scripts, `vidts` treats all inputs as generic domain documents with flexible content profiles.

### Key Highlights
- **Local-First & Resource Efficient**: Designed to run comfortably on Windows 11 with 16 GB RAM and no dedicated GPU, delegating intelligence to local models (e.g. Gemma 3) running via Ollama.
- **Provider-Agnostic LLM Architecture**: Relies on a pluggable `LLMProvider` interface rather than hardcoding vendor APIs.
- **Document-Agnostic Model**: Generic representations (`Document`, `DocumentPage`, `DocumentSection`, `Recap`, `DocumentSegment`) instead of comic-only concepts.
- **Configurable Pacing & Segmentation**: Keeps documents as single coherent videos when within duration/word limits, splitting into multi-part series only when necessary.

---

## Supported Document Types

`vidts` will generically ingest and analyze varied document formats:

1. **Manhwa / Manga / Comic PDFs**: Visual-heavy documents with panel pacing and dialogue cues.
2. **Textbooks**: Chapter-dense technical or domain materials with definitions and diagrams.
3. **Educational PDFs & Lecture Notes**: Concept-driven lecture slides and study guides.
4. **Research Papers**: Academic articles featuring abstracts, methodologies, findings, and figures.
5. **Novels & Books**: Narrative-driven literary works requiring narrative arc summaries.
6. **General Documents**: Whitepapers, technical manuals, and standard reports.

---

## Architecture

The system follows a modular 6-stage pipeline where every stage is decoupled and testable via dependency injection:

```
PDF Document
     │
     ▼
[Stage 1: Document Ingestion] ──► (app/ingest)
     │ Extracts pages, raw text, and dimensions (ready for OCR extension)
     ▼
[Stage 2: Document Analysis]  ──► (app/analysis)
     │ Classifies document type, detects density, structural sections
     ▼
[Stage 3: Recap Generation]   ──► (app/recap)
     │ Prompts local LLM via LLMProvider with external templates
     ▼
[Stage 4: Segmentation]       ──► (app/segmentation)
     │ Enforces max duration/words; splits into parts only when needed
     ▼
[Stage 5: Narration]          ──► (app/narration)
     │ Abstracted TTS interface (Piper, Edge TTS, Coqui, etc.)
     ▼
[Stage 6: Video Rendering]    ──► (app/video)
     │ Assembles page visuals, animations, audio tracks, and subtitles
     ▼
Final Video Output (.mp4)
```

### Directory Structure

```
vidts/
├── app/
│   ├── __init__.py            # Custom domain exceptions (VidtsError, etc.)
│   ├── main.py                # Command-line interface entrypoint
│   ├── config.py              # Strongly-typed configuration dataclasses
│   ├── pipeline.py            # Orchestrator coordinating all 6 stages
│   │
│   ├── ingest/                # PDF ingestion and page extraction
│   │   ├── __init__.py
│   │   ├── pdf_parser.py
│   │   ├── page_extractor.py
│   │   └── models.py
│   │
│   ├── analysis/              # Document classification & structural analysis
│   │   ├── __init__.py
│   │   ├── document_analyzer.py
│   │   └── models.py
│   │
│   ├── recap/                 # LLM-powered recap script generation
│   │   ├── __init__.py
│   │   ├── recap_generator.py
│   │   ├── prompts.py
│   │   └── models.py
│   │
│   ├── segmentation/          # Intelligent video part partitioning
│   │   ├── __init__.py
│   │   ├── segmenter.py
│   │   └── models.py
│   │
│   ├── narration/             # Text-to-speech narration abstractions
│   │   ├── __init__.py
│   │   ├── narrator.py
│   │   └── models.py
│   │
│   ├── video/                 # Video assembly and rendering abstractions
│   │   ├── __init__.py
│   │   ├── renderer.py
│   │   └── models.py
│   │
│   └── llm/                   # Pluggable LLM interfaces and providers
│       ├── __init__.py
│       ├── base.py
│       ├── ollama.py
│       └── models.py
│
├── prompts/                   # Externalized LLM prompt templates
│   ├── recap.txt
│   ├── document_analysis.txt
│   └── segmentation.txt
│
├── tests/                     # Comprehensive test suite with LLM mocks
│   ├── __init__.py
│   ├── test_ingest.py
│   ├── test_analysis.py
│   ├── test_recap.py
│   ├── test_segmentation.py
│   └── test_pipeline.py
│
├── examples/                  # Sample inputs and walkthroughs
│   └── README.md
│
├── output/                    # Generated audio/video target folder
│   └── .gitkeep
│
├── config.yaml                # Default application configuration
├── requirements.txt           # All dependencies (runtime + testing)
├── .gitignore                 # Standard Python & project ignore rules
├── pyproject.toml             # Modern packaging and tool configuration
└── README.md
```

---

## Current Status

- [x] Extensible modular architecture with typed domain models.
- [x] Abstract `LLMProvider` interface and local `OllamaProvider`.
- [x] Configurable YAML settings loader with fallback defaults.
- [x] PDF text extraction and dimension calculation layer.
- [x] External prompt loading for story recaps and analysis.
- [x] Pacing and segmentation logic respecting duration and word constraints.
- [x] Working CLI with validation and logging.
- [x] Independent unit tests with mock LLM providers (no server dependency).
- [ ] *Placeholder*: OCR for scanned / image-only PDFs.
- [ ] *Placeholder*: Full TTS engine binding (Piper / Edge TTS / Kokoro).
- [ ] *Placeholder*: Final FFmpeg / MoviePy video compositing.

---

## Installation

### Prerequisites
- Python 3.11+ (tested on Python 3.13)
- Windows 11 / Linux / macOS

### Setup

```bash
# Clone the repository
git clone https://github.com/your-username/vidts.git
cd vidts

# Create and activate a virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

---

## Ollama Setup

`vidts` uses Ollama for local LLM inference.

1. Download and install [Ollama](https://ollama.com).
2. Start the Ollama server:
   ```bash
   ollama serve
   ```
3. Pull your preferred model (default configured is `gemma3`):
   ```bash
   ollama pull gemma3
   ```

You can change the target model at any time in `config.yaml`.

---

## Configuration

Settings are managed via `config.yaml`:

```yaml
llm:
  provider: ollama
  model: gemma3
  base_url: "http://localhost:11434"
  timeout_seconds: 120

document:
  max_pages: null # Optional integer to limit parsing (e.g. 50)

segmentation:
  enabled: true
  max_duration_minutes: 10
  max_script_words: 1800
  max_pages_per_video: null

output:
  directory: "output"

video:
  resolution: "1920x1080"
  fps: 30
```

---

## Running the Project

### Display CLI Help

```bash
python -m app.main --help
```

### Run on a PDF Document

```bash
python -m app.main path/to/document.pdf
```

### Specify a Custom Configuration or Log Level

```bash
python -m app.main path/to/document.pdf --config custom_config.yaml --log-level DEBUG
```

---

## Testing

Run all unit tests with `pytest`:

```bash
pytest
```

Tests run completely offline without needing a running Ollama server.

---

## Future Roadmap

1. **Stage 1 (Ingest)**: Add lightweight OCR support (e.g. Tesseract / RapidOCR) for scanned PDFs.
2. **Stage 2 (Analysis)**: Vision-language model integration to extract comic panels and textbook diagram captions.
3. **Stage 3 (Recap)**: Dynamic style templates (e.g. dramatic comic narration vs. concise academic explainer).
4. **Stage 5 (Narration)**: Native integration with high-quality local TTS (Piper, Kokoro, Edge-TTS).
5. **Stage 6 (Video)**: Motion effects (Ken Burns pan/zoom on panels), waveform visualization, and automated subtitle burnt-in rendering.
