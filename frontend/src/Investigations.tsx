import { useState, type FormEvent } from 'react';
import { api, download, percent, pretty } from './client';
import type { URLReport, EmailReport, Indicator } from './types';

export const EMAIL_DEMO =
  'From: "security@example.org" <notice@sender.example.test>\nReply-To: support@reply.example.invalid\nSubject: Urgent account verification — synthetic demo\nMIME-Version: 1.0\nContent-Type: text/html; charset=utf-8\nAuthentication-Results: forged.example.test; spf=pass; dkim=pass; dmarc=pass\n\n<p>Your account will be suspended. Verify your account immediately.</p><p>Never enter a password; this is a harmless synthetic fixture.</p><a href="http://account-verify.example.test/login/secure?user=demo">https://example.org</a>';
function Indicators({ items }: { items: Indicator[] }) {
  return items.length ? (
    <ul className="indicators">
      {items.map((i, k) => (
        <li key={i.code + k}>
          <span className="tiny-dot" />
          <div>
            <b>{pretty(i.code)}</b>
            <p>{i.message}</p>
          </div>
          <small>{i.kind === 'heuristic' ? 'URL rule' : 'Email rule'}</small>
        </li>
      ))}
    </ul>
  ) : (
    <p className="muted">No configured indicators matched. This does not establish safety.</p>
  );
}
export function URLResult({ report }: { report: URLReport }) {
  const exp = report.explanation;
  const max = Math.max(...(exp?.items.map((x) => Math.abs(x.contribution)) ?? [1]), 0.00001);
  return (
    <div className="result-stack">
      <section className="panel result-hero">
        <div>
          <span className="eyebrow">ANALYSIS RESULT</span>
          <h2>{pretty(report.classification)}</h2>
          <p className="mono wrap">{report.input.host}</p>
          <p>{report.score_meaning}</p>
        </div>
        <div className="score">
          <strong>{percent(report.score)}</strong>
          <span>model estimate</span>
          <small>Threshold {percent(report.threshold)}</small>
        </div>
      </section>
      {report.review_reasons.length > 0 && (
        <div className="notice" role="status">
          <b>Analyst review required</b>
          <ul>
            {report.review_reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="two-col">
        <section className="panel">
          <div className="section-title">
            <h3>Observed signals</h3>
            <span className="tag">Independent heuristics</span>
          </div>
          <Indicators items={report.heuristics} />
          <details>
            <summary>All lexical features ({Object.keys(report.observed_features).length})</summary>
            <dl className="features">
              {Object.entries(report.observed_features).map(([k, v]) => (
                <div key={k}>
                  <dt>{pretty(k)}</dt>
                  <dd>{Number.isInteger(v) ? v : v.toFixed(3)}</dd>
                </div>
              ))}
            </dl>
          </details>
        </section>
        <section className="panel">
          <div className="section-title">
            <h3>Model explanation</h3>
            <span className="tag">{exp?.additive ? 'Linear contributions' : 'Sensitivity'}</span>
          </div>
          {exp ? (
            <>
              <p className="muted">{exp.method}</p>
              <div className="contributions">
                {exp.items.map((i) => (
                  <div key={i.feature}>
                    <span className="mono">{i.feature}</span>
                    <div className="track">
                      <i
                        className={i.contribution < 0 ? 'negative' : ''}
                        style={{ width: `${(Math.abs(i.contribution) / max) * 100}%` }}
                      />
                    </div>
                    <span>
                      {i.contribution > 0 ? '+' : ''}
                      {i.contribution.toFixed(3)}
                    </span>
                  </div>
                ))}
              </div>
              <p className="caption">Positive values support the phishing direction. {exp.note}</p>
            </>
          ) : (
            <p>No model explanation is available without an installed model.</p>
          )}
        </section>
      </div>
      <section className="panel provenance">
        <div>
          <span className="eyebrow">PROVENANCE</span>
          <p className="mono">
            {report.model_id ?? 'No model'} · v{report.model_version ?? '—'}
          </p>
        </div>
        <div>
          <span className="eyebrow">INPUT SHA-256</span>
          <p className="mono wrap">{report.input_sha256}</p>
        </div>
        <button
          className="secondary"
          onClick={() => download(report, 'phishguard-url-report.json')}
        >
          Export JSON ↓
        </button>
      </section>
      <p className="caption">{report.limitations.join(' ')}</p>
    </div>
  );
}
export function URLInvestigation() {
  const [value, setValue] = useState('');
  const [result, setResult] = useState<URLReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setResult(null);
    if (!/^https?:\/\//i.test(value)) {
      setError('Enter an absolute HTTP(S) URL.');
      return;
    }
    setBusy(true);
    try {
      setResult(
        await api<URLReport>('/analyze/url', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: value }),
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed.');
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <span className="eyebrow">01 / URL INVESTIGATION</span>
        <h1>
          Inspect the link.
          <br />
          <em>Keep it unopened.</em>
        </h1>
        <p>Offline lexical analysis with traceable model signals and visible uncertainty.</p>
      </div>
      <section className="panel">
        <form onSubmit={submit}>
          <label htmlFor="url-input">URL to investigate</label>
          <div className="input-row">
            <input
              id="url-input"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              maxLength={4096}
              placeholder="https://example.org/resource"
              required
              autoComplete="off"
              spellCheck={false}
            />
            <button disabled={busy}>{busy ? 'Analyzing…' : 'Analyze URL ↗'}</button>
          </div>
        </form>
        <div className="samples">
          <span>Synthetic samples:</span>
          <button onClick={() => setValue('https://example.org/articles/security-basics')}>
            Benign-looking
          </button>
          <button
            onClick={() => setValue('http://account-verify.example.test/login/secure?user=demo')}
          >
            Suspicious pattern
          </button>
        </div>
        <p className="caption">
          No page retrieval, DNS request, or reputation lookup. Submitted URLs stay in this local
          session.
        </p>
      </section>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {result ? (
        <URLResult report={result} />
      ) : (
        <div className="empty">
          <span>⌁</span>
          <h3>Ready for a closer look</h3>
          <p>Enter a URL to see observed features, model estimates and an explanation.</p>
        </div>
      )}
    </>
  );
}
export function EmailInvestigation() {
  const [content, setContent] = useState('');
  const [result, setResult] = useState<EmailReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function send(init: RequestInit, path = '/analyze/email') {
    setBusy(true);
    setError('');
    setResult(null);
    try {
      setResult(await api<EmailReport>(path, init));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Email analysis failed.');
    } finally {
      setBusy(false);
    }
  }
  async function upload(file: File | undefined) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.eml') || file.size > 262144) {
      setError('Choose an .eml file up to 256 KiB.');
      return;
    }
    await send(
      {
        method: 'POST',
        headers: { 'Content-Type': 'message/rfc822', 'X-Filename': file.name },
        body: file,
      },
      '/analyze/email-file',
    );
  }
  return (
    <>
      <div className="page-heading">
        <span className="eyebrow">02 / EMAIL INVESTIGATION</span>
        <h1>
          Read the evidence.
          <br />
          <em>Question the claims.</em>
        </h1>
        <p>Safe MIME inspection and URL-level inference. No trained email classifier is implied.</p>
      </div>
      <section className="panel">
        <div className="section-title">
          <h3>Message source</h3>
          <button className="text-button" onClick={() => setContent(EMAIL_DEMO)}>
            Load synthetic message
          </button>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void send({
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ content }),
            });
          }}
        >
          <label htmlFor="email-input">Paste message text or raw email</label>
          <textarea
            id="email-input"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            maxLength={262144}
            rows={8}
            required
            placeholder="From: sender@example.org&#10;Subject: A message to investigate"
          />
          <div className="section-title">
            <label className="upload">
              Upload .eml
              <input
                type="file"
                accept=".eml,message/rfc822"
                onChange={(e) => void upload(e.target.files?.[0])}
              />
            </label>
            <button disabled={busy}>{busy ? 'Inspecting…' : 'Analyze email ↗'}</button>
          </div>
        </form>
        <p className="caption">
          256 KiB maximum · 100 MIME parts · 20 URL analyses · no attachment execution or saved
          history
        </p>
      </section>
      {error && (
        <div role="alert" className="error">
          {error}
        </div>
      )}
      {result && (
        <div className="result-stack">
          <section className="panel">
            <div className="section-title">
              <div>
                <span className="eyebrow">MESSAGE FINDINGS</span>
                <h2>{pretty(result.classification)}</h2>
              </div>
              <button
                className="secondary"
                onClick={() => download(result, 'phishguard-email-report.json')}
              >
                Export JSON ↓
              </button>
            </div>
            <dl className="metadata">
              <dt>Subject</dt>
              <dd>{result.subject}</dd>
              <dt>From</dt>
              <dd>
                {result.from.map((x) => `${x.display} <${x.address}>`).join(', ') || 'Missing'}
              </dd>
              <dt>Reply-To</dt>
              <dd>{result.reply_to.map((x) => x.address).join(', ') || 'Not present'}</dd>
              <dt>Input size</dt>
              <dd>{result.bytes.toLocaleString()} bytes</dd>
            </dl>
          </section>
          <div className="two-col">
            <section className="panel">
              <h3>Email indicators</h3>
              <Indicators items={result.indicators} />
            </section>
            <section className="panel">
              <span className="tag amber">UNVERIFIED HEADER CLAIMS</span>
              <h3>Authentication observations</h3>
              <p>{result.authentication.note}</p>
              {result.authentication.reported_claims.length ? (
                result.authentication.reported_claims.map((x, i) => <pre key={i}>{x}</pre>)
              ) : (
                <p className="muted">No Authentication-Results header present.</p>
              )}
            </section>
          </div>
          <section className="panel">
            <div className="section-title">
              <h3>Extracted links</h3>
              <span className="tag">{result.url_count} observed</span>
            </div>
            {result.urls_truncated && (
              <p className="notice">Analysis is limited to the first 20 unique URLs.</p>
            )}
            {result.url_reports.map((r, i) => (
              <div className="link-result" key={i}>
                <code>{r.url}</code>
                <div>
                  <span>{pretty(r.analysis?.classification ?? 'unsupported input')}</span>
                  <b>{percent(r.analysis?.score)}</b>
                </div>
                {r.error && <p>{r.error}</p>}
              </div>
            ))}
          </section>
          <section className="panel">
            <h3>Text-only body</h3>
            <pre className="message-body">{result.body_text}</pre>
            {result.body_truncated && <p>Text preview truncated.</p>}
            {result.attachments.length > 0 && (
              <>
                <h3>Attachments — metadata only</h3>
                {result.attachments.map((a, i) => (
                  <p key={i}>
                    <code>{a.name}</code> · {a.content_type}
                  </p>
                ))}
              </>
            )}
          </section>
          <p className="caption">
            {result.method} {result.limitations.join(' ')}
          </p>
        </div>
      )}
    </>
  );
}
