import { useEffect, useRef, useState } from "react";
import {
  Activity,
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  Cpu,
  Download,
  Dna,
  FileText,
  FlaskConical,
  Layers3,
  Menu,
  Microscope,
  Network,
  ScanLine,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from "lucide-react";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const workflowSteps = [
  { icon: Upload, number: "01", title: "Upload FASTA", text: "Bring a .fasta, .fa, or .fna sequence file into the workspace." },
  { icon: ShieldCheck, number: "02", title: "DNA validation", text: "Check sequence integrity and identify unsupported characters." },
  { icon: ScanLine, number: "03", title: "Preprocessing", text: "Encode A, C, G, and T using the trained input contract." },
  { icon: Cpu, number: "04", title: "1D-CNN inference", text: "Run the installed experimental viral-family classifier." },
  { icon: FileText, number: "05", title: "Results & report", text: "Review statistics, predictions, and download a PDF report." },
];

function App() {
  const [connection, setConnection] = useState({ status: "checking", message: "Checking backend..." });
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadState, setUploadState] = useState({ status: "idle", message: "" });
  const [summary, setSummary] = useState(null);
  const [reportState, setReportState] = useState("idle");
  const [predictionState, setPredictionState] = useState({ status: "idle", message: "", predictions: [], model: null });
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    let active = true;
    fetch(`${apiBaseUrl}/api/health`)
      .then((response) => {
        if (!response.ok) throw new Error("Backend returned an error");
        return response.json();
      })
      .then((data) => {
        if (active) setConnection({ status: "connected", message: data.status });
      })
      .catch(() => {
        if (active) setConnection({ status: "offline", message: "Backend unavailable" });
      });
    return () => {
      active = false;
    };
  }, []);

  const chooseFile = (file) => {
    if (!file) return;
    setSelectedFile(file);
    setSummary(null);
    setPredictionState({ status: "idle", message: "", predictions: [], model: null });
    setUploadState({ status: "idle", message: "" });
  };

  const clearFile = () => {
    setSelectedFile(null);
    setSummary(null);
    setPredictionState({ status: "idle", message: "", predictions: [], model: null });
    setUploadState({ status: "idle", message: "" });
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleUpload = async (event) => {
    event.preventDefault();
    if (!selectedFile) return;
    setUploadState({ status: "uploading", message: "Validating and parsing sequence..." });
    const formData = new FormData();
    formData.append("file", selectedFile);
    try {
      const response = await fetch(`${apiBaseUrl}/api/uploads/fasta`, { method: "POST", body: formData });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Upload failed.");
      await new Promise((resolve) => setTimeout(resolve, 600));
      setSummary(data);
      setUploadState({ status: "success", message: data.message });
      document.getElementById("results")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      setUploadState({ status: "error", message: error.message });
    }
  };

  const downloadReport = async () => {
    if (!selectedFile) return;
    setReportState("loading");
    const formData = new FormData();
    formData.append("file", selectedFile);
    if (predictionState.predictions.length > 0) {
      formData.append("predictions_json", JSON.stringify(predictionState.predictions));
      formData.append("model_metadata_json", JSON.stringify(predictionState.model || {}));
    }
    try {
      const response = await fetch(`${apiBaseUrl}/api/uploads/report`, { method: "POST", body: formData });
      if (!response.ok) throw new Error("Could not generate the PDF report.");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "deepgenelens-analysis.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setReportState("ready");
    } catch {
      setReportState("error");
    }
  };

  const runPrediction = async () => {
    if (!selectedFile) return;
    setPredictionState({ status: "loading", message: "Running trained model...", predictions: [], model: null });
    const formData = new FormData();
    formData.append("file", selectedFile);
    try {
      const response = await fetch(`${apiBaseUrl}/api/analysis/predict`, { method: "POST", body: formData });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Prediction failed.");
      setPredictionState({ status: "success", message: "", predictions: data.predictions, model: data.model });
    } catch (error) {
      setPredictionState({ status: "error", message: error.message, predictions: [], model: null });
    }
  };

  return (
    <main className="app-shell">
      <nav className="navbar">
        <a className="brand" href="#home" aria-label="DeepGeneLens home">
          <span className="brand-mark"><Dna size={20} /></span>
          <span>DeepGene<span className="brand-accent">Lens</span></span>
        </a>
        <button className="mobile-menu" type="button" aria-label="Toggle navigation" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
          {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
        <div className={`nav-links ${mobileMenuOpen ? "open" : ""}`}>
          <a href="#home" onClick={() => setMobileMenuOpen(false)}>Home</a>
          <a href="#analysis" onClick={() => setMobileMenuOpen(false)}>DNA Analysis</a>
          <a href="#model" onClick={() => setMobileMenuOpen(false)}>Model Insights</a>
          <a href="#about" onClick={() => setMobileMenuOpen(false)}>About</a>
          <a href={`${apiBaseUrl}/docs`} target="_blank" rel="noreferrer">API Docs <ChevronRight size={14} /></a>
          <span className={`health-pill ${connection.status}`}><span /> {connection.status === "connected" ? "Backend healthy" : connection.message}</span>
        </div>
      </nav>

      <section className="hero-section" id="home">
        <div className="hero-content">
          <div className="prototype-label"><span className="pulse-dot" /> Experimental research platform</div>
          <h1>Unlock insights<br />hidden in <em>DNA.</em></h1>
          <p>Explore DNA sequences through intelligent genomic analysis and experimental AI-powered viral family classification.</p>
          <div className="hero-actions">
            <a className="button button-primary" href="#analysis">Upload FASTA <ArrowRight size={17} /></a>
            <a className="button button-ghost" href="#workflow">Explore platform <ChevronRight size={17} /></a>
          </div>
          <div className="hero-note"><ShieldCheck size={16} /> Built for responsible genomic research</div>
        </div>
        <div className="hero-visual" aria-label="DNA research visualization">
          <div className="visual-orbit orbit-one" /><div className="visual-orbit orbit-two" />
          <div className="dna-core"><Dna size={184} strokeWidth={1.15} /></div>
          <div className="data-chip chip-top"><span className="chip-dot orange" /> A · C · G · T <small>BASES</small></div>
          <div className="data-chip chip-right"><Activity size={14} /> 1D-CNN <small>MODEL</small></div>
          <div className="visual-caption">Sequence intelligence<br /><strong>01 / 04</strong></div>
        </div>
      </section>

      <section className="metric-strip" aria-label="Verified project metrics">
        <div><strong>712</strong><span>selected RefSeq sequences</span></div>
        <div><strong>12</strong><span>viral family classes</span></div>
        <div><strong>1D-CNN</strong><span>PyTorch architecture</span></div>
        <div><strong>63.96%</strong><span>held-out test accuracy</span></div>
        <p>Dataset &amp; model metrics · not live usage statistics</p>
      </section>

      <section className="analysis-section section-wrap" id="analysis">
        <div className="section-intro">
          <div><p className="eyebrow">01 / DNA ANALYSIS</p><h2>Start with your sequence.</h2><p>Upload a FASTA file to run transparent sequence statistics, validation, and the installed research model.</p></div>
          <div className="section-side-note"><FlaskConical size={18} /><span>Real data processing<br /><strong>Biopython + PyTorch</strong></span></div>
        </div>
        <div className="upload-workspace">
          <div
            className={`drop-zone ${selectedFile ? "has-file" : ""}`}
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => { event.preventDefault(); chooseFile(event.dataTransfer.files?.[0]); }}
          >
            <input ref={fileInputRef} type="file" accept=".fasta,.fa,.fna" onChange={(event) => chooseFile(event.target.files?.[0])} />
            <div className="drop-icon"><Upload size={23} /></div>
            <h3>{selectedFile ? selectedFile.name : "Drop your FASTA file here"}</h3>
            <p>{selectedFile ? `${(selectedFile.size / 1024).toFixed(1)} KB · Ready to analyze` : "or browse from your computer"}</p>
            {!selectedFile && <button className="button button-outline" type="button" onClick={() => fileInputRef.current?.click()}>Browse files <ArrowRight size={15} /></button>}
            {selectedFile && <button className="file-remove" type="button" onClick={clearFile}><X size={14} /> Remove file</button>}
            <small>Supported: .fasta · .fa · .fna &nbsp;|&nbsp; Max 10 MB</small>
          </div>
          <form className="analysis-controls" onSubmit={handleUpload}>
            <div className="control-heading"><span className="step-number">01</span><div><strong>Analyze sequence</strong><span>Validate and calculate DNA composition</span></div></div>
            <button type="submit" className="button button-primary full-button" disabled={!selectedFile || uploadState.status === "uploading"}>
              {uploadState.status === "uploading" ? "Processing..." : "Analyze DNA"} <ArrowRight size={16} />
            </button>
            <div className="control-status">
              <span className={`status-indicator ${uploadState.status}`} />
              {uploadState.status === "success" ? "Analysis ready" : uploadState.status === "error" ? uploadState.message : "Your file stays in this session"}
            </div>
          </form>
        </div>
      </section>

      <section className="workflow-section section-wrap" id="workflow">
        <div className="center-intro"><p className="eyebrow">02 / HOW IT WORKS</p><h2>From sequence to signal.</h2><p>A clear, auditable workflow from raw nucleotide data to experimental insight.</p></div>
        <div className="workflow-grid">{workflowSteps.map(({ icon: Icon, number, title, text }) => <article className="workflow-item" key={number}><div className="workflow-icon"><Icon size={19} /></div><span className="workflow-number">{number}</span><h3>{title}</h3><p>{text}</p></article>)}</div>
      </section>

      <section className="model-section section-wrap" id="model">
        <div className="model-copy"><p className="eyebrow">03 / MODEL INSIGHTS</p><h2>A focused model for a focused question.</h2><p>The current baseline uses real NCBI RefSeq data and a compact PyTorch 1D-CNN to explore viral family classification. Every output is marked research-only.</p><div className="model-details"><span><Cpu size={16} /> PyTorch 1D-CNN</span><span><Layers3 size={16} /> 12 classes</span><span><Dna size={16} /> A/C/G/T encoding</span><span><Network size={16} /> 4,096-base input</span></div></div>
        <div className="architecture-card"><div className="arch-header"><span>MODEL ARCHITECTURE</span><span className="arch-status"><span /> CPU READY</span></div><div className="arch-flow"><div className="arch-node"><Dna size={18} /><strong>DNA</strong><small>4 channels</small></div><ChevronRight /><div className="arch-node"><Layers3 size={18} /><strong>CONV 1D</strong><small>32 · 64 · 128</small></div><ChevronRight /><div className="arch-node"><Sparkles size={18} /><strong>CLASSIFIER</strong><small>12 families</small></div></div><div className="model-score"><strong>63.96%</strong><span>held-out accuracy<br />weighted F1 59.75%</span></div></div>
      </section>

      {summary && <section className="results-section section-wrap" id="results" aria-label="Analysis results">
        <div className="results-heading"><div><p className="eyebrow">04 / ANALYSIS COMPLETE</p><h2>Your sequence, decoded.</h2><p>Computed from <strong>{summary.filename}</strong> with Biopython.</p></div><button type="button" className="button button-outline" onClick={downloadReport} disabled={reportState === "loading"}><Download size={16} /> {reportState === "loading" ? "Generating..." : "Download PDF report"}</button></div>
        {reportState === "error" && <div className="notice error"><AlertCircle size={16} /> Report generation failed. Please try again.</div>}
        <div className="results-grid">
          <article className="result-card"><div className="card-title"><FileText size={17} /> Analysis summary</div><div className="stat-list"><div><span>File name</span><strong>{summary.filename}</strong></div><div><span>Total sequences</span><strong>{summary.sequence_count}</strong></div><div><span>Total bases</span><strong>{summary.total_bases.toLocaleString()}</strong></div><div><span>Validation</span><strong className={summary.valid ? "valid" : "invalid"}>{summary.valid ? "Valid DNA" : `Invalid (${summary.invalid_base_count} bases)`}</strong></div></div></article>
          <article className="result-card"><div className="card-title"><Dna size={17} /> DNA composition</div><div className="composition-grid">{["A", "T", "G", "C"].map((base) => <div key={base}><strong>{summary.composition[base].toFixed(2)}%</strong><span>{base} nucleotide</span></div>)}</div><div className="gc-bar-label"><span>GC content</span><strong>{summary.gc_content.toFixed(2)}%</strong></div><div className="gc-bar"><span style={{ width: `${summary.gc_content}%` }} /></div></article>
          <article className="result-card sequence-card"><div className="card-title"><Activity size={17} /> Sequence details</div><div className="sequence-table"><div className="table-row table-header"><span>Sequence ID</span><span>Length</span><span>GC content</span></div>{summary.records.map((record) => <div className="table-row" key={record.id}><span>{record.id}</span><span>{record.length.toLocaleString()} bases</span><span>{record.gc_content.toFixed(2)}%</span></div>)}</div></article>
          <article className="prediction-card"><div className="prediction-heading"><div className="card-title"><Microscope size={17} /> AI prediction <span>{predictionState.status === "success" ? "RESEARCH MODEL" : "MODEL READY TO RUN"}</span></div><button type="button" className="button button-primary" onClick={runPrediction} disabled={predictionState.status === "loading"}>{predictionState.status === "loading" ? "Running..." : "Run trained model"} <ArrowRight size={15} /></button></div>{predictionState.status === "error" && <div className="notice error"><AlertCircle size={16} /> {predictionState.message}</div>}{predictionState.predictions.length > 0 && <div className="prediction-list">{predictionState.predictions.map((prediction) => <div key={prediction.sequence_id}><span>{prediction.sequence_id}</span><strong>{prediction.predicted_family}</strong><em>{(prediction.confidence * 100).toFixed(2)}%</em></div>)}</div>}<p>{predictionState.status === "success" ? "Generated by the installed experimental PyTorch model. No clinical conclusion is implied." : "Run the installed experimental model to classify valid DNA sequences. No clinical conclusion is implied."}</p></article>
        </div>
      </section>}

      <section className="responsible-section section-wrap" id="about"><div className="responsible-icon"><ShieldCheck size={25} /></div><div><p className="eyebrow">RESPONSIBLE RESEARCH</p><h2>Built to explore, not to diagnose.</h2><p>DeepGeneLens is an experimental research prototype. Predictions are not clinically validated and must not be used for medical diagnosis or treatment decisions.</p></div></section>

      <footer className="footer"><div className="footer-brand"><a className="brand" href="#home"><span className="brand-mark"><Dna size={18} /></span><span>DeepGene<span className="brand-accent">Lens</span></span></a><p>Intelligent tools for genomic research.</p></div><div className="footer-column"><strong>Platform</strong><a href="#analysis">DNA Analysis</a><a href="#model">Model Insights</a><a href={`${apiBaseUrl}/docs`} target="_blank" rel="noreferrer">API Docs</a></div><div className="footer-column"><strong>Technology</strong><span>React + Vite</span><span>FastAPI + Biopython</span><span>PyTorch 1D-CNN</span></div><div className="footer-meta"><span>Research prototype · v0.1.0</span><span>© 2026 DeepGeneLens</span></div></footer>
    </main>
  );
}

export default App;
