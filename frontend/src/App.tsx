import { useEffect, useState } from 'react';
import { api, percent } from './client';
import type { ModelInfo, Research } from './types';
import { URLInvestigation, EmailInvestigation } from './Investigations';
import { ResearchLab, Documentation, Metric } from './Research';
type Screen =
  'Overview' | 'URL analysis' | 'Email investigation' | 'Research laboratory' | 'Model & dataset';
const pages: Screen[] = [
  'Overview',
  'URL analysis',
  'Email investigation',
  'Research laboratory',
  'Model & dataset',
];
export default function App() {
  const [screen, setScreen] = useState<Screen>('Overview');
  const [info, setInfo] = useState<ModelInfo | null>(null);
  const [research, setResearch] = useState<Research | null>(null);
  const [status, setStatus] = useState('Connecting to local API…');
  useEffect(() => {
    let alive = true;
    void Promise.allSettled([
      api<ModelInfo>('/model/info'),
      api<Research>('/research/summary'),
    ]).then(([m, r]) => {
      if (!alive) return;
      if (m.status === 'fulfilled') {
        setInfo(m.value);
        setStatus(m.value.available ? 'Local model ready' : 'Rules-only mode');
      } else setStatus('API unavailable — start the local backend');
      if (r.status === 'fulfilled') setResearch(r.value);
    });
    return () => {
      alive = false;
    };
  }, []);
  const chosen = research?.models.find(
    (m) => m.protocol === 'domain_disjoint' && m.model === research.selected_model,
  );
  return (
    <div className="app-shell">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            P<span>G</span>
          </div>
          <div>
            <b>
              PhishGuard <span>AI</span>
            </b>
            <small>RESEARCH WORKSPACE</small>
          </div>
        </div>
        <span className="nav-label">INVESTIGATE & EVALUATE</span>
        <nav aria-label="Main navigation">
          {pages.map((p, i) => (
            <button
              key={p}
              onClick={() => setScreen(p)}
              aria-current={screen === p ? 'page' : undefined}
              className={screen === p ? 'active' : ''}
            >
              <span className="nav-symbol">{['◈', '↗', '▤', '⌁', '▧'][i]}</span>
              {p}
              <span className="nav-number">0{i}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="status-light" />
          <b>Designed for local analysis</b>
          <p>
            No URL visits.
            <br />
            No cloud inference.
            <br />
            No stored message history.
          </p>
          <span className="mono">BUILD 1.0.0</span>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <span>
            Workspace <span className="slash">/</span> <b>{screen}</b>
          </span>
          <span className="system-status">
            <i className={info ? 'status-light' : 'status-light amber-light'} />
            {status}
          </span>
        </header>
        <main id="main" tabIndex={-1}>
          {screen === 'Overview' && (
            <>
              <div className="overview-hero">
                <div>
                  <span className="eyebrow">EXPLAINABLE PHISHING RESEARCH</span>
                  <h1>
                    Evidence before
                    <br />
                    <em>verdicts.</em>
                  </h1>
                  <p>
                    Investigate a suspicious link or message.
                    <br />
                    See the signals, examine the model, understand the uncertainty.
                  </p>
                  <div className="hero-actions">
                    <button onClick={() => setScreen('URL analysis')}>
                      Start an investigation ↗
                    </button>
                    <button className="secondary" onClick={() => setScreen('Research laboratory')}>
                      Explore the research
                    </button>
                  </div>
                </div>
                <div className="signal-visual" aria-hidden="true">
                  <div className="orbit orbit-one" />
                  <div className="orbit orbit-two" />
                  <div className="crosshair" />
                  <div className="signal-core">
                    PG<span>OFFLINE ANALYSIS</span>
                  </div>
                  <span className="signal-label signal-top">LEXICAL SIGNALS</span>
                  <span className="signal-label signal-bottom">EXPLAINABLE ESTIMATES</span>
                  <i className="signal-node one" />
                  <i className="signal-node two" />
                  <i className="signal-node three" />
                </div>
              </div>
              <div className="stat-grid">
                <Metric
                  label="EXPERIMENT SAMPLES"
                  value={research?.dataset.sample_rows.toLocaleString() ?? '—'}
                  sub="Real UCI data · fixed-seed subset"
                />
                <Metric
                  label="UNSEEN-DOMAIN F1"
                  value={chosen?.metrics.f1.toFixed(4) ?? '—'}
                  sub="Selected model · held-out test"
                />
                <Metric
                  label="PHISHING RECALL"
                  value={percent(chosen?.metrics.recall)}
                  sub="Dataset-specific, not a safety guarantee"
                />
                <Metric
                  label="CALIBRATION ECE"
                  value={chosen?.metrics.ece?.toFixed(4) ?? '—'}
                  sub="10 equal-width bins · lower is better"
                />
              </div>
              <div className="overview-lower">
                <section className="panel">
                  <div className="section-title">
                    <h3>Investigation workbench</h3>
                    <span className="tag">LOCAL / SINGLE USER</span>
                  </div>
                  <button className="workbench" onClick={() => setScreen('URL analysis')}>
                    <span className="feature-icon">↗</span>
                    <span>
                      <b>URL intelligence</b>
                      <small>Lexical evidence, calibrated estimates, model contributions</small>
                    </span>
                    <span>→</span>
                  </button>
                  <button className="workbench" onClick={() => setScreen('Email investigation')}>
                    <span className="feature-icon">▤</span>
                    <span>
                      <b>Email inspection</b>
                      <small>MIME structure, sender claims, embedded links</small>
                    </span>
                    <span>→</span>
                  </button>
                  <button className="workbench" onClick={() => setScreen('Research laboratory')}>
                    <span className="feature-icon">⌁</span>
                    <span>
                      <b>Research laboratory</b>
                      <small>Holdout protocols, feature ablations, perturbation sensitivity</small>
                    </span>
                    <span>→</span>
                  </button>
                </section>
                <section className="panel model-summary">
                  <span className="eyebrow">CURRENT MODEL</span>
                  <h2 className="mono">{info?.model_id ?? 'Awaiting model'}</h2>
                  <span className="tag">
                    {info?.available ? 'VALIDATION-SELECTED' : 'MODEL UNAVAILABLE'}
                  </span>
                  <p>
                    Selected using held-out domain validation. Calibration and final evaluation use
                    separate data partitions.
                  </p>
                  <dl>
                    <div>
                      <dt>Representation</dt>
                      <dd>
                        {chosen?.kind === 'char'
                          ? 'Character TF-IDF + logistic regression'
                          : 'Offline lexical features'}
                      </dd>
                    </div>
                    <div>
                      <dt>Inference</dt>
                      <dd>Local · data-only model artifact</dd>
                    </div>
                  </dl>
                  <button className="text-button" onClick={() => setScreen('Model & dataset')}>
                    Read model & dataset notes →
                  </button>
                </section>
              </div>
              <div className="notice subtle">
                <b>Investigation support, not a definitive verdict.</b> Unusual URLs can be
                legitimate. Plausible-looking URLs can be malicious. Review the evidence before
                acting. High benchmark scores also reflect dataset formatting bias; inspect the
                HTTPS/www diagnostic in the research laboratory.
              </div>
            </>
          )}
          {screen === 'URL analysis' && <URLInvestigation />}
          {screen === 'Email investigation' && <EmailInvestigation />}
          {screen === 'Research laboratory' && <ResearchLab data={research} />}
          {screen === 'Model & dataset' && <Documentation info={info} data={research} />}
        </main>
        <footer>
          <span>
            PHISHGUARD AI <span className="slash">/</span> EXPLAINABLE SECURITY RESEARCH
          </span>
          <span>Observe. Evaluate. Investigate.</span>
        </footer>
      </div>
    </div>
  );
}
