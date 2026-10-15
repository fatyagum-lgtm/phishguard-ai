export type Indicator = { code: string; message: string; kind: string; weight?: number };
export type Explanation = {
  method: string;
  additive: boolean;
  baseline: number | null;
  total_raw_score: number;
  items: { feature: string; contribution: number }[];
  note: string;
};
export type URLReport = {
  kind: 'url';
  input: { original: string; normalized: string; host: string; domain: string; scheme: string };
  classification: string;
  binary_model_label: string | null;
  score: number | null;
  threshold: number | null;
  score_meaning: string;
  model_id: string | null;
  model_version: string | null;
  review_reasons: string[];
  observed_features: Record<string, number>;
  heuristics: Indicator[];
  rule_index: number;
  explanation: Explanation | null;
  analysis_ms: number;
  limitations: string[];
  input_sha256: string;
};
export type EmailReport = {
  kind: 'email';
  subject: string;
  from: { display: string; address: string }[];
  reply_to: { display: string; address: string }[];
  body_text: string;
  body_truncated: boolean;
  attachments: { name: string; content_type: string; encoded_characters: number | null }[];
  authentication: { verified: boolean; reported_claims: string[]; note: string };
  indicators: Indicator[];
  classification: string;
  method: string;
  url_count: number;
  urls_truncated: boolean;
  url_reports: { url: string; analysis: URLReport | null; error: string | null }[];
  limitations: string[];
  input_sha256: string;
  bytes: number;
  defects: string[];
};
export type Metrics = {
  n: number;
  threshold: number;
  precision: number;
  recall: number;
  f1: number;
  fpr: number | null;
  fnr: number | null;
  roc_auc: number | null;
  average_precision: number | null;
  brier: number | null;
  ece: number | null;
  confusion_matrix: number[][];
  reliability: { mean_score: number; positive_fraction: number; count: number }[];
  f1_interval?: { low: number; high: number; groups: number; repeats: number };
};
export type ModelResult = {
  protocol: string;
  model: string;
  kind: string;
  metrics: Metrics;
  curves: { pr: number[][]; roc: number[][] };
  training_seconds?: number;
  model_json_bytes?: number;
  latency?: { median_ms: number; p95_ms: number; batch_urls_per_second: number };
  raw_at_05?: Metrics;
  calibrated_at_05?: Metrics;
  errors?: { kind: string; url_defanged: string; score: number; label: number }[];
};
export type Robustness = {
  exploratory?: boolean;
  category: string;
  model: string;
  n: number;
  scope: string;
  changed_inputs: number;
  mean_absolute_delta: number;
  max_absolute_delta: number;
  flip_rate: number;
  review_rate_before: number;
  review_rate_after: number;
  rule_finding_change_rate: number;
  example: { before: string; after: string; score_before: number; score_after: number };
};
export type Dataset = {
  input_rows: number;
  invalid_rows: number;
  duplicate_rows_removed: number;
  conflicting_label_rows_removed: number;
  clean_rows: number;
  sample_rows: number;
  sample_domains: number;
  sample_phishing: number;
  archive_sha256: string;
  source: string;
  license: string;
  near_duplicate_template_rows: number;
};
export type Research = {
  collection_bias?: {
    by_label: {
      label: number;
      rows: number;
      https_fraction: number;
      www_prefix_fraction: number;
    }[];
  };
  generated_utc: string;
  dataset: Dataset;
  seed: number;
  smoke: boolean;
  models: ModelResult[];
  selected_model: string;
  selected_artifact_bytes: number;
  robustness: Robustness[];
  elapsed_seconds: number;
  limitations: string[];
  protocols: Record<
    string,
    {
      chosen: string;
      partitions: Record<string, { rows: number; domains: number; phishing: number }>;
      overlaps: { pair: string; exact_urls: number; domains: number; templates: number }[];
    }
  >;
  environment: { python: string; platform: string; libraries: Record<string, string> };
};
export type ModelInfo = {
  available: boolean;
  error: string | null;
  model_id: string | null;
  version: string;
  threshold: number | null;
  protocol: string | null;
  dataset: Dataset | null;
  score_note: string;
  limits: Record<string, number>;
};
