/* Editorial Signal implementation: a public, document-first conversion flow where uploads stay central and sign-in is strictly optional. */
import { useRef, useState } from "react";
import {
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronRight,
  CirclePlay,
  Clock3,
  FileText,
  FolderOpen,
  Mail,
  Play,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from "lucide-react";

const acceptableFiles = ".pdf,.doc,.docx,.ppt,.pptx,.txt,.rtf";

function Hourglass() {
  return (
    <div className="hourglass-wrap" aria-hidden="true">
      <div className="hourglass-shadow" />
      <div className="hourglass-frame">
        <span className="frame-cap top" />
        <div className="glass-body">
          <span className="sand upper-sand" />
          <span className="sand-stream" />
          <span className="sand lower-sand" />
        </div>
        <span className="frame-cap bottom" />
      </div>
    </div>
  );
}

function AuthModal({ onClose, onNotice }) {
  return (
    <div className="auth-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="auth-dialog" role="dialog" aria-modal="true" aria-labelledby="signin-title" onMouseDown={(event) => event.stopPropagation()}>
        <button className="dialog-close" type="button" aria-label="Close sign in" onClick={onClose}><X size={18} /></button>
        <img className="dialog-mark" src="/manus-storage/vidts-symbol_f3a9ffe3.png" alt="" />
        <p className="dialog-eyebrow">Optional account</p>
        <h2 id="signin-title">Keep your videos together.</h2>
        <p className="dialog-copy">Sign in to save projects and revisit your video drafts. You can still create a video without an account.</p>
        <div className="auth-options">
          <button type="button" onClick={() => onNotice("Google sign-in can be connected when authentication is added.") }><span className="auth-google">G</span> Continue with Google</button>
          <button type="button" onClick={() => onNotice("Facebook sign-in can be connected when authentication is added.") }><span className="auth-facebook">f</span> Continue with Facebook</button>
          <button type="button" onClick={() => onNotice("Email sign-up can be connected when authentication is added.") }><Mail size={16} /> Continue with email</button>
        </div>
        <button className="guest-link" type="button" onClick={onClose}>Continue as guest <ArrowRight size={15} /></button>
      </section>
    </div>
  );
}

export default function Home() {
  const inputRef = useRef(null);
  const timerRef = useRef(null);
  const [file, setFile] = useState(null);
  const [stage, setStage] = useState("idle");
  const [dragging, setDragging] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [notice, setNotice] = useState("");

  const shortName = file ? file.name.replace(/\.[^/.]+$/, "") : "Your document";

  function selectFile(selectedFile) {
    if (!selectedFile) return;
    setFile(selectedFile);
    setStage("ready");
    setNotice(`${selectedFile.name} is ready to turn into a video.`);
  }

  function handleFileChange(event) {
    selectFile(event.target.files?.[0]);
    event.target.value = "";
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragging(false);
    selectFile(event.dataTransfer.files?.[0]);
  }

  function makeVideo() {
    if (!file) {
      inputRef.current?.click();
      return;
    }
    setNotice("");
    setStage("processing");
    window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => setStage("ready-video"), 5600);
  }

  function useDemo() {
    selectFile(new File(["demo"], "The-neighborhood-notebook.pdf", { type: "application/pdf" }));
  }

  return (
    <div className="public-app">
      <header className="public-nav">
        <a className="brand-lockup" href="#top" aria-label="vidts home">
          <img className="brand-mark" src="/manus-storage/vidts-symbol_f3a9ffe3.png" alt="vidts" />
          <span className="wordmark">vidts</span>
        </a>
        <nav className="nav-links" aria-label="Page navigation">
          <a href="#how-it-works">The method</a>
          <a href="#privacy">Your source</a>
        </nav>
        <button className="signin-button" type="button" onClick={() => setAuthOpen(true)}>Sign in <ChevronRight size={16} /></button>
      </header>

      <main id="top">
        {stage === "processing" ? (
          <section className="processing-stage" aria-live="polite">
            <div className="processing-copy">
              <p className="eyebrow"><Sparkles size={15} /> In the studio</p>
              <h1>Giving your document a new rhythm.</h1>
              <p className="processing-lead">We’re finding the narrative, choosing visual beats, and setting the first cut in motion.</p>
              <div className="processing-steps">
                <span><Check size={14} /> Reading your pages</span>
                <span className="active"><i /> Composing your video</span>
                <span>Preparing the final cut</span>
              </div>
            </div>
            <div className="hourglass-panel">
              <Hourglass />
              <p className="sand-caption">The upper chamber is clearing</p>
              <strong>Turning pages into scenes</strong>
              <span>Usually less than a minute</span>
            </div>
          </section>
        ) : stage === "ready-video" ? (
          <section className="ready-stage">
            <div className="ready-copy">
              <p className="eyebrow"><CheckCircle2 size={15} /> First cut complete</p>
              <h1>Your story is ready to watch.</h1>
              <p>We made a 57-second first video from <strong>{file?.name}</strong>. It is waiting for your review.</p>
              <div className="ready-actions">
                <button className="primary-action" type="button" onClick={() => setNotice("Video preview opened — connect your generation service to render the final file.") }><Play size={16} fill="currentColor" /> Watch the first cut</button>
                <button className="text-action" type="button" onClick={() => { setFile(null); setStage("idle"); }}>Start another <ArrowRight size={15} /></button>
              </div>
              {notice && <div className="inline-notice"><Check size={14} /> {notice}</div>}
            </div>
            <div className="video-poster" style={{ backgroundImage: "url(/manus-storage/vidts-editorial-hero_b5ca2001.jpg)" }}>
              <div className="poster-wash" />
              <div className="poster-header"><span>VIDTS / FIRST CUT</span><span>00:57</span></div>
              <div className="poster-bottom">
                <span>{shortName}</span>
                <CirclePlay size={48} strokeWidth={1.3} />
              </div>
            </div>
          </section>
        ) : (
          <section className="hero-stage">
            <div className="hero-copy">
              <p className="eyebrow"><Sparkles size={15} /> Documents in. Watchable stories out.</p>
              <h1>Turn a document into a video with a point of view.</h1>
              <p className="hero-lead">Drop in your PDF, Word file, slide deck, or notes. vidts shapes the material into a short, clear video you can watch and share.</p>
              <div className="trust-line" id="privacy"><ShieldCheck size={16} /><span>No account required. Your upload stays yours.</span></div>
            </div>

            <div className="upload-card-wrap">
              <div
                className={`upload-card ${dragging ? "is-dragging" : ""} ${file ? "has-file" : ""}`}
                onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
              >
                <input ref={inputRef} id="document-upload" type="file" accept={acceptableFiles} onChange={handleFileChange} />
                <div className="source-strip"><span><i className="minute-glass" /> SOURCE / 01</span><span>FIRST CUT / 01:00</span></div>
                {file ? (
                  <div className="selected-file">
                    <div className="file-icon"><FileText size={25} /></div>
                    <div className="file-name"><span>Ready to shape</span><strong>{file.name}</strong><small>{file.type === "application/pdf" ? "PDF document" : "Document"} · ready for a first cut</small></div>
                    <button type="button" aria-label="Remove selected file" onClick={() => { setFile(null); setStage("idle"); setNotice(""); }}><X size={17} /></button>
                  </div>
                ) : (
                  <label className="upload-empty" htmlFor="document-upload">
                    <span className="paper-index">01</span>
                    <span className="upload-symbol"><Upload size={25} /></span>
                    <strong>Set your source on the desk</strong>
                    <span>Drop it here, or choose it from your device</span>
                    <small>PDF, Word, slides, or text · up to 100 MB</small>
                  </label>
                )}
                <button className="primary-action upload-action" type="button" onClick={makeVideo}>{file ? "Start the first cut" : "Place a document on the desk"}<ArrowRight size={17} /></button>
              </div>
              <div className="upload-footer"><span><Clock3 size={14} /> The first cut is usually ready in a minute</span><button type="button" onClick={useDemo}>Set a sample on the desk <ChevronRight size={14} /></button></div>
              {notice && <div className="inline-notice"><Check size={14} /> {notice}</div>}
            </div>

            <div className="hero-aside" aria-hidden="true">
              <div className="hero-image" style={{ backgroundImage: "url(/manus-storage/vidts-studio-still_924ab1c9.jpg)" }} />
              <span className="side-note note-one">Page 03</span>
              <span className="side-note note-two">First cut</span>
              <span className="side-rule" />
            </div>
          </section>
        )}

        <section className="how-section" id="how-it-works">
          <div className="how-title"><p className="eyebrow">From source to screen</p><h2>One document. A considered first cut.</h2><p>vidts treats the first pass like an editor would: find the thread, arrange the moments, and put the story on screen.</p></div>
          <div className="how-steps">
            <article><span className="step-time">00:00</span><div className="step-symbol"><FileText size={19} /></div><div><p className="step-label">Set the source</p><h3>Lay the pages on the desk.</h3><p>Bring the document you already have. No special formatting, no prompt wrangling.</p></div></article>
            <article><span className="step-time">00:15</span><div className="step-symbol"><Sparkles size={19} /></div><div><p className="step-label">Mark the thread</p><h3>Find the part that carries.</h3><p>We look for the essential movement and shape it into scenes, voice, and pace.</p></div></article>
            <article><span className="step-time">00:57</span><div className="step-symbol"><CirclePlay size={19} /></div><div><p className="step-label">Screen the cut</p><h3>Watch the first version.</h3><p>Get a compact video draft to review, share, or take into the next editing pass.</p></div></article>
          </div>
        </section>
      </main>

      <footer className="public-footer"><span>© 2026 vidts</span><span>Made for ideas that deserve a second form.</span><button type="button" onClick={() => setAuthOpen(true)}>Save work with an account</button></footer>
      {authOpen && <AuthModal onClose={() => setAuthOpen(false)} onNotice={(message) => { setAuthOpen(false); setNotice(message); }} />}
    </div>
  );
}
