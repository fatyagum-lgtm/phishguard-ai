import { useState } from 'react';
import type { Research as ResearchData, ModelInfo } from './types';
import { percent, pretty, download } from './client';
import { LineChart, Confusion } from './Charts';

export function ResearchLab({ data }: { data: ResearchData | null }) {
  const [protocol, setProtocol] = useState('domain_disjoint');
  const [model, setModel] = useState('');
  const [sort, setSort] = useState<'f1' | 'recall' | 'precision'>('f1');
  if (!data)
    return (
      <div className="empty">
        <h2>No experiment artifact available</h2>
        <p>Run the research workflow and install its report to populate this laboratory.</p>
      </div>
    );
  const models = data.models.filter((m) => m.protocol === protocol);
  const selected =
    models.find((m) => m.model === model) ??
    models.find((m) => m.model === data.selected_model) ??
    models[0];
  const robust = data.robustness.filter((r) => r.model === selected.model);
  const bins = selected.metrics.reliability;
  const cm = selected.metrics.confusion_matrix;
  return (
    <>
      <div className="page-heading">
        <span className="eyebrow">03 / RESEARCH LABORATORY</span>
        <h1>
          Measure the model.
          <br />
          <em>Expose its limits.</em>
        </h1>
        <p>
          Computed results from {data.dataset.sample_rows.toLocaleString()} UCI samples.{' '}
          {data.smoke ? 'Reduced smoke experiment.' : 'Fixed-seed subset experiment.'} No live
          website features.
        </p>
      </div>
      <div className="toolbar">
        <label>
          Evaluation protocol
          <select
            value={protocol}
            onChange={(e) => {
              setProtocol(e.target.value);
              setModel('');
            }}
          >
            <option value="domain_disjoint">Domain-disjoint holdout</option>
            <option value="random">Stratified random holdout</option>
          </select>
        </label>
        <label>
          Inspect model
          <select value={selected.model} onChange={(e) => setModel(e.target.value)}>
            {models.map((m) => (
              <option key={m.model}>{m.model}</option>
            ))}
          </select>
        </label>
        <button className="secondary" onClick={() => download(data, 'phishguard-research.json')}>
          Download experiment ↓
        </button>
      </div>
      <div className="stat-grid">
        <Metric
          label="PRECISION"
          value={percent(selected.metrics.precision)}
          sub="Phishing predictions that match labels"
        />
        <Metric
          label="RECALL"
          value={percent(selected.metrics.recall)}
          sub="Labeled phishing samples detected"
        />
        <Metric
          label="F1 SCORE"
          value={selected.metrics.f1.toFixed(4)}
          sub={
            selected.metrics.f1_interval
              ? `95% cluster interval ${selected.metrics.f1_interval.low.toFixed(3)}–${selected.metrics.f1_interval.high.toFixed(3)}`
              : 'Fixed rule baseline'
          }
        />
        <Metric
          label="BRIER SCORE"
          value={selected.metrics.brier?.toFixed(4) ?? 'Not applicable'}
          sub="Probability loss · lower is better"
        />
      </div>
      {data.collection_bias && (
        <section className="notice">
          <b>High scores can conceal collection bias.</b>
          <p>
            In the domain-disjoint training partition,{' '}
            {data.collection_bias.by_label.map((r) => (
              <span key={r.label}>
                {r.label === 0 ? 'legitimate' : 'phishing'} URLs use HTTPS in{' '}
                {percent(r.https_fraction)} and a www prefix in {percent(r.www_prefix_fraction)} of
                cases.{' '}
              </span>
            ))}
            These are dataset associations, not evidence of safety. This post-hoc diagnostic was not
            used to retune the model.
          </p>
        </section>
      )}
      <section className="panel">
        <div className="section-title">
          <h3>Model comparison</h3>
          <span className="tag">{selected.metrics.n.toLocaleString()} test samples</span>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Model</th>
                {(['precision', 'recall', 'f1'] as const).map((k) => (
                  <th key={k}>
                    <button className="sort" onClick={() => setSort(k)}>
                      {pretty(k)} {sort === k ? '↓' : '↕'}
                    </button>
                  </th>
                ))}
                <th>FPR</th>
                <th>ROC-AUC</th>
                <th>AP</th>
                <th>ECE</th>
              </tr>
            </thead>
            <tbody>
              {[...models]
                .sort((a, b) => b.metrics[sort] - a.metrics[sort])
                .map((m) => (
                  <tr key={m.model} className={m.model === selected.model ? 'selected-row' : ''}>
                    <th>
                      <button className="text-button mono" onClick={() => setModel(m.model)}>
                        {m.model}
                      </button>
                    </th>
                    <td>{percent(m.metrics.precision)}</td>
                    <td>{percent(m.metrics.recall)}</td>
                    <td>{m.metrics.f1.toFixed(4)}</td>
                    <td>{percent(m.metrics.fpr)}</td>
                    <td>{m.metrics.roc_auc?.toFixed(4)}</td>
                    <td>{m.metrics.average_precision?.toFixed(4)}</td>
                    <td>{m.metrics.ece?.toFixed(4) ?? '—'}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
        <p className="caption">
          Threshold {selected.metrics.threshold.toFixed(2)} selected on validation. Rules use a
          fixed threshold and an uncalibrated indicator index. AP is average precision, not
          trapezoidal PR area.
        </p>
      </section>
      <div className="two-col">
        <section className="panel">
          <h3>Confusion matrix</h3>
          <Confusion values={cm} />
        </section>
        <section className="panel">
          <h3>Partition integrity</h3>
          <div className="partition-bars">
            {Object.entries(data.protocols[protocol].partitions).map(([k, v]) => (
              <div key={k}>
                <span>{pretty(k)}</span>
                <div className="track">
                  <i style={{ width: `${(v.rows / data.dataset.sample_rows) * 100}%` }} />
                </div>
                <strong>{v.rows.toLocaleString()}</strong>
              </div>
            ))}
          </div>
          <p className="muted">
            Exact URL overlap:{' '}
            {data.protocols[protocol].overlaps.reduce((n, v) => n + v.exact_urls, 0)} across all
            partition pairs.
          </p>
          <p className="caption">
            {protocol === 'domain_disjoint'
              ? 'All registrable-domain groups are separated. Group fractions need not equal sample fractions.'
              : 'Domain overlap is allowed in this comparison protocol; normalized duplicates are still separated.'}
          </p>
        </section>
      </div>
      <div className="chart-grid">
        <section className="panel">
          <LineChart
            title="Precision–recall"
            points={selected.curves.pr}
            xLabel="Recall"
            yLabel="Precision"
          />
        </section>
        <section className="panel">
          <LineChart
            title="ROC curve"
            points={selected.curves.roc}
            xLabel="False-positive rate"
            yLabel="True-positive rate"
            color="#8bafff"
          />
        </section>
        <section className="panel">
          {bins.length ? (
            <LineChart
              title="Calibration reliability"
              points={bins.map((b) => [b.mean_score, b.positive_fraction])}
              xLabel="Mean model estimate"
              yLabel="Observed phishing fraction"
              diagonal
            />
          ) : (
            <div className="empty compact">
              <h3>No calibrated probabilities</h3>
              <p>The rule index is not a probability.</p>
            </div>
          )}
        </section>
      </div>
      {selected.raw_at_05 && (
        <section className="panel">
          <h3>Calibration comparison</h3>
          <p>
            At the same 0.50 decision threshold, raw Brier loss was{' '}
            <b>{selected.raw_at_05.brier?.toFixed(4)}</b>; after sigmoid calibration it was{' '}
            <b>{selected.calibrated_at_05?.brier?.toFixed(4)}</b>. ECE:{' '}
            {selected.raw_at_05.ece?.toFixed(4)} → {selected.calibrated_at_05?.ece?.toFixed(4)}.
          </p>
          <p className="caption">
            Calibration uses a separate partition. Lower Brier loss reflects both reliability and
            discrimination; it does not independently establish general-world calibration.
          </p>
        </section>
      )}
      <section className="panel">
        <div className="section-title">
          <h3>Controlled perturbations</h3>
          <span className="tag">Offline sensitivity study</span>
        </div>
        <p className="muted">
          Host casing and unreserved encoding use real holdout inputs. Other transformations use
          reserved-domain synthetic examples, without label-preservation claims.
        </p>
        {robust.length ? (
          <div className="robust-bars">
            {robust.map((r) => (
              <div key={r.category}>
                <div>
                  <b>
                    {pretty(r.category)}
                    {r.exploratory ? ' · exploratory' : ''}
                  </b>
                  <span>
                    {r.n} pairs · {percent(r.flip_rate)} label flips
                  </span>
                </div>
                <div className="track">
                  <i style={{ width: `${r.mean_absolute_delta * 100}%` }} />
                </div>
                <strong>
                  {r.mean_absolute_delta > 0 && r.mean_absolute_delta < 0.0001
                    ? r.mean_absolute_delta.toExponential(1)
                    : r.mean_absolute_delta.toFixed(4)}
                </strong>
                <details>
                  <summary>Inspect paired example</summary>
                  <p className="mono wrap">{r.example.before}</p>
                  <p className="mono wrap">{r.example.after}</p>
                  <p>
                    {r.example.score_before.toFixed(4)} → {r.example.score_after.toFixed(4)}
                  </p>
                </details>
              </div>
            ))}
          </div>
        ) : (
          <p>
            No perturbation study was run for this ablation model. Select the character model, full
            forest or rules.
          </p>
        )}
        <p className="caption">
          Bars show mean absolute score change on a 0–1 scale. Instability is not evidence of a
          working evasion attack.
        </p>
      </section>
      {selected.errors && (
        <section className="panel">
          <h3>Representative errors</h3>
          <p className="muted">
            Largest score-to-threshold distances among held-out errors. Dataset labels are not
            independently reverified; examples are defanged.
          </p>
          <div className="error-examples">
            {selected.errors.map((e, i) => (
              <div key={i}>
                <span className="tag amber">{pretty(e.kind)}</span>
                <code>{e.url_defanged}</code>
                <b>{percent(e.score)}</b>
              </div>
            ))}
          </div>
        </section>
      )}
      <section className="panel">
        <h3>What this experiment cannot establish</h3>
        <ul className="plain-list">
          {data.limitations.map((x) => (
            <li key={x}>{x}</li>
          ))}
        </ul>
      </section>
    </>
  );
}
export function Metric({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="metric">
      <span className="eyebrow">{label}</span>
      <strong>{value}</strong>
      <p>{sub}</p>
    </div>
  );
}
export function Documentation({
  info,
  data,
}: {
  info: ModelInfo | null;
  data: ResearchData | null;
}) {
  return (
    <>
      <div className="page-heading">
        <span className="eyebrow">04 / MODEL & DATASET NOTES</span>
        <h1>
          Know what
          <br />
          <em>the estimate means.</em>
        </h1>
        <p>Provenance, reproducibility and boundaries are part of the result.</p>
      </div>
      <div className="two-col">
        <section className="panel">
          <h3>Deployed model</h3>
          <dl className="metadata">
            <dt>Identity</dt>
            <dd className="mono">{info?.model_id ?? 'No model installed'}</dd>
            <dt>Version</dt>
            <dd>{info?.version ?? '—'}</dd>
            <dt>Selection</dt>
            <dd>Domain-disjoint validation F1; Brier and FPR break ties</dd>
            <dt>Calibration</dt>
            <dd>Separate 10% group calibration partition; two-parameter sigmoid</dd>
            <dt>Threshold</dt>
            <dd>{info?.threshold?.toFixed(2) ?? '—'}</dd>
            <dt>Artifact</dt>
            <dd>Data-only JSON; no executable pickle deserialization</dd>
          </dl>
        </section>
        <section className="panel">
          <h3>Dataset provenance</h3>
          <dl className="metadata">
            <dt>Source</dt>
            <dd>UCI PhiUSIIL, dataset 967 · Prasad & Chandra (2024)</dd>
            <dt>License</dt>
            <dd>CC BY 4.0</dd>
            <dt>Source rows</dt>
            <dd>{data?.dataset.input_rows.toLocaleString() ?? '—'}</dd>
            <dt>Clean rows</dt>
            <dd>{data?.dataset.clean_rows.toLocaleString() ?? '—'}</dd>
            <dt>Experiment rows</dt>
            <dd>{data?.dataset.sample_rows.toLocaleString() ?? '—'}</dd>
            <dt>Labels</dt>
            <dd>UCI 0 = phishing, 1 = legitimate. Internal 1 = phishing.</dd>
          </dl>
        </section>
      </div>
      <section className="panel">
        <h3>Reproduce the study</h3>
        <pre>
          python -m phishguard.cli acquire{'\n'}python -m phishguard.cli research --samples 40000
          --seed 2026 --output reports/runs/reproduction
        </pre>
        <p>
          Run from the repository root in the installed Python environment. Use a new output
          directory. No sample URL is visited. See README and docs/experimental-methodology.md for
          exact dependency locks and model installation.
        </p>
      </section>
      <section className="panel">
        <h3>Trust boundaries</h3>
        <ul className="plain-list">
          <li>Local single-user application. Analysis inputs are not persisted by the server.</li>
          <li>Email HTML is converted to text. Attachments are not opened or executed.</li>
          <li>
            Authentication-Results is an unverified message claim, not an SPF/DKIM/DMARC check.
          </li>
          <li>Model outputs support investigation. They cannot certify a URL or sender as safe.</li>
          <li>
            Synthetic demo domains are outside validated public-domain inference; review is
            required.
          </li>
        </ul>
      </section>
      <section className="panel">
        <h3>Actual experiment environment</h3>
        <pre>
          {data ? JSON.stringify(data.environment, null, 2) : 'No experiment metadata installed.'}
        </pre>
      </section>
    </>
  );
}
