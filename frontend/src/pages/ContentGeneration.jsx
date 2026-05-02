import { useEffect, useMemo, useRef, useState } from "react";
import * as XLSX from "xlsx";
import StepIndicator from "../components/StepIndicator";
import RecommendationCard from "../components/RecommendationCard";
import PipelineTimeline from "../components/PipelineTimeline";
import { useJob } from "../context/jobHooks";
import "../styles/ContentGeneration.css";

const STEPS = [
  "Upload Inventory",
  "AI Recommendations",
  "Review & Select",
  "Generated Content",
];

const PREVIEW_ROW_LIMIT = 8;

function isValidDate(value) {
  if (value === null || value === undefined || value === "") return true;
  if (value instanceof Date) return !isNaN(value.getTime());
  const s = String(value).trim();
  if (!s) return true;

  // Try YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
    const d = new Date(s);
    return !isNaN(d.getTime());
  }

  // Try DD/MM/YYYY or D/M/YYYY (common in Malaysia/UK)
  if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(s)) {
    const parts = s.split('/');
    const day = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10);
    const year = parseInt(parts[2], 10);
    const d = new Date(year, month - 1, day);
    return d.getFullYear() === year && d.getMonth() === month - 1 && d.getDate() === day;
  }

  const d = new Date(s);
  return !isNaN(d.getTime());
}

function validateRow(row, rowIndex) {
  const num = rowIndex + 2;
  if (!row.product_name || !String(row.product_name).trim()) return `Row ${num}: 'product_name' is required.`;
  if (!row.category || !String(row.category).trim()) return `Row ${num}: 'category' is required.`;
  if (row.stock_level !== 0 && !row.stock_level) return `Row ${num}: 'stock_level' is required.`;
  if (isNaN(parseFloat(row.stock_level))) return `Row ${num}: 'stock_level' must be a number (got '${row.stock_level}').`;
  if (row.price !== 0 && !row.price) return `Row ${num}: 'price' is required.`;
  if (isNaN(parseFloat(row.price))) return `Row ${num}: 'price' must be a number (got '${row.price}').`;
  if (row.date_added && !isValidDate(row.date_added)) return `Row ${num}: 'date_added' must be a valid date (got '${row.date_added}').`;
  if (row.expiry_date && !isValidDate(row.expiry_date)) return `Row ${num}: 'expiry_date' must be a valid date (got '${row.expiry_date}').`;
  return null;
}
const REQUIRED_COLUMNS = [
  "product_name",
  "category",
  "stock_level",
  "price",
];

/** Lightweight client-side preview (first N rows). Backend re-parses for real. */
function processFile(file, onProgress, onComplete) {
  const reader = new FileReader();
  reader.onload = async (e) => {
    try {
      const data = new Uint8Array(e.target.result);
      const workbook = XLSX.read(data, { type: "array" });
      const worksheet = workbook.Sheets[workbook.SheetNames[0]];
      const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
      if (!jsonData || jsonData.length === 0) {
        onComplete({ columns: [], rows: [], totalRows: 0, error: "File is empty." });
        return;
      }
      const columns = jsonData[0].map(c => String(c || "").trim());
      const headersLower = columns.map(c => c.toLowerCase());
      const missing = REQUIRED_COLUMNS.filter(req => !headersLower.includes(req.toLowerCase()));
      if (missing.length > 0) {
        onComplete({ columns, rows: [], totalRows: 0, error: `Missing required columns: ${missing.join(", ")}` });
        return;
      }
      const allRows = jsonData.slice(1);
      const total = allRows.length;
      for (let i = 0; i < total; i++) {
        const rowArr = allRows[i];
        if (!rowArr || rowArr.length === 0) continue;
        const row = {};
        columns.forEach((col, j) => {
          // Normalize key for validation
          row[col.toLowerCase()] = rowArr[j];
          // Preserve original key for preview
          row[col] = rowArr[j];
        });
        const error = validateRow(row, i);
        if (error) {
          onComplete({ columns, rows: [], totalRows: total, error });
          return;
        }
        if (total > 0 && i % 20 === 0) {
          onProgress(Math.round((i / total) * 100));
          await new Promise(r => setTimeout(r, 0));
        }
      }
      const previewRows = allRows.slice(0, PREVIEW_ROW_LIMIT).map(rowArr => {
        const row = {};
        columns.forEach((col, j) => { row[col] = rowArr[j] ?? ""; });
        return row;
      });
      onProgress(100);
      onComplete({ columns, rows: previewRows, totalRows: total });
    } catch (err) {
      console.error("File process error:", err);
      onComplete({ columns: [], rows: [], totalRows: 0, error: "Failed to read file." });
    }
  };
  reader.readAsArrayBuffer(file);
}

function ErrorBanner({ error, onDismiss, onRetry, retryLabel }) {
  if (!error) return null;
  const detail = error.detail;
  const hasParts = detail && typeof detail === "object" && detail.completed;
  return (
    <div className="gen-error-banner" role="alert">
      <div className="gen-error-banner__head">
        <strong>{error.message || "Something went wrong."}</strong>
        <div className="gen-error-banner__actions">
          {onRetry && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={onRetry}
            >
              {retryLabel || "Try again"}
            </button>
          )}
          {onDismiss && (
            <button
              type="button"
              className="gen-error-banner__close"
              onClick={onDismiss}
              aria-label="Dismiss"
            >
              ×
            </button>
          )}
        </div>
      </div>
      {hasParts && (
        <div className="gen-error-banner__parts">
          {Object.entries(detail.completed).map(([part, ok]) => (
            <span
              key={part}
              className={`gen-error-banner__part ${ok ? "gen-error-banner__part--ok" : "gen-error-banner__part--fail"}`}
            >
              {ok ? "✓" : "✕"} {part}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ContentGeneration() {
  const job = useJob();
  const {
    status,
    phase,
    currentStepIndex,
    startedAt,
    campaignLabel,
    area: jobArea,
    phaseAResponse,
    selectedIdx,
    finalResult,
    error,
    notification,
  } = job;
  const {
    startPhaseA,
    startPhaseB,
    setSelectedIdx,
    reset,
    dismissError,
    dismissNotification,
  } = job.actions;

  // Local UI-only state (file/preview/copy state — not part of the pipeline).
  const [uploadedFile, setUploadedFile] = useState(null);
  const [csvPreview, setCsvPreview] = useState({
    columns: [],
    rows: [],
    totalRows: 0,
    missingColumns: [],
  });
  const [dragOver, setDragOver] = useState(false);
  const [areaOverride, setAreaOverride] = useState("");
  const [reviewMode, setReviewMode] = useState(false);
  const [copiedField, setCopiedField] = useState(null);
  const [validationError, setValidationError] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [validationProgress, setValidationProgress] = useState(0);
  const fileInputRef = useRef(null);

  // Clear the indicator's "done" pill when the user lands here.
  useEffect(() => {
    if (notification) dismissNotification();
  }, [notification, dismissNotification]);

  /* ---------------------- step indicator computation ---------------------- */

  const indicatorStep = useMemo(() => {
    if (status === "completed") return 4;
    if (status === "error") {
      if (error?.phase === "B") return 3;
      return 1;
    }
    if (status === "running" && phase === "A") return 1;
    if (status === "running" && phase === "B") return 3;
    if (status === "awaiting") return reviewMode ? 3 : 2;
    return 1;
  }, [status, phase, error, reviewMode]);

  /* ----------------------------- file handling ---------------------------- */

  const ingestFile = (file) => {
    if (!file) return;
    setUploadedFile(file);
    setValidationError(null);
    setIsValidating(true);
    setValidationProgress(0);

    processFile(
      file,
      (progress) => setValidationProgress(progress),
      (result) => {
        setIsValidating(false);
        if (result.error) {
          setValidationError(result.error);
          setCsvPreview({ columns: [], rows: [], totalRows: 0, missingColumns: [] });
        } else {
          setCsvPreview({
            columns: result.columns,
            rows: result.rows,
            totalRows: result.totalRows,
            missingColumns: []
          });
          setValidationError(null);
        }
      }
    );
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) ingestFile(file);
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) ingestFile(file);
  };

  /* ----------------------------- API actions ----------------------------- */

  const handleAnalyse = () => {
    if (!uploadedFile) return;
    setReviewMode(false);
    startPhaseA({
      file: uploadedFile,
      area: areaOverride.trim() || undefined,
      count: 2,
    });
  };

  const handleProceed = () => {
    if (selectedIdx == null) return;
    setReviewMode(true);
  };

  const handleGenerate = () => {
    startPhaseB();
  };

  const handleReset = () => {
    reset();
    setUploadedFile(null);
    setCsvPreview({ columns: [], rows: [], totalRows: 0, missingColumns: [] });
    setAreaOverride("");
    setReviewMode(false);
  };

  const handleRetry = () => {
    if (error?.phase === "A") {
      handleAnalyse();
    } else if (error?.phase === "B") {
      startPhaseB();
    }
  };

  const copyToClipboard = (text, field) => {
    if (!navigator?.clipboard?.writeText) return;
    navigator.clipboard.writeText(text).then(() => {
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    });
  };

  /* ----------------------------- derived data ---------------------------- */

  const recommendations = useMemo(() => {
    if (!phaseAResponse?.strategies) return [];
    return phaseAResponse.strategies.map((opt, idx) => ({
      id: idx,
      platform: opt.strategy.platform,
      format: opt.strategy.format,
      product: opt.featured_product.product,
      audience: opt.strategy.audience,
      pricing: opt.strategy.pricing,
      bestTime: opt.strategy.timing,
      reason:
        opt.rationale ||
        `Targets ${opt.featured_product.product} on ${opt.strategy.platform}.`,
    }));
  }, [phaseAResponse]);

  const liveContext = phaseAResponse?.live_context;
  const riskCounts = useMemo(() => {
    if (!phaseAResponse?.risk_analysis) return null;
    return {
      high: phaseAResponse.risk_analysis.high_risk?.length || 0,
      medium: phaseAResponse.risk_analysis.medium_risk?.length || 0,
      low: phaseAResponse.risk_analysis.low_risk?.length || 0,
    };
  }, [phaseAResponse]);

  const generated = useMemo(() => {
    if (!finalResult) return null;
    const variants = finalResult.content?.content_variants || [];
    const primary = variants[0] || {};
    const allHashtags = Array.from(
      new Set(variants.flatMap((v) => v.hashtags || [])),
    );
    return {
      platform:
        phaseAResponse?.strategies?.[selectedIdx]?.strategy?.platform || "—",
      format:
        phaseAResponse?.strategies?.[selectedIdx]?.strategy?.format || "—",
      product: finalResult.metadata?.featured_product?.product || "",
      adCopy: [primary.headline, primary.caption, primary.call_to_action]
        .filter(Boolean)
        .join("\n\n"),
      captions: variants.map((v) => v.caption).filter(Boolean),
      hashtags: allHashtags,
      image: finalResult.content?.image?.url || (finalResult.content?.image?.base64
        ? `data:${finalResult.content.image.mime_type};base64,${finalResult.content.image.base64}`
        : null),
      explanation: finalResult.explanation,
      imagePrompt: finalResult.content?.image_prompt || "",
    };
  }, [finalResult, phaseAResponse, selectedIdx]);

  /* ----------------------------- view flags ----------------------------- */

  const isRunning = status === "running";
  const isPhaseAError = status === "error" && error?.phase === "A";
  const isPhaseBError = status === "error" && error?.phase === "B";

  const showUploadStep = status === "idle" || isPhaseAError;
  const showRunningTimeline = isRunning;
  const showPicker = status === "awaiting" && !reviewMode;
  const showReview =
    (status === "awaiting" && reviewMode) || isPhaseBError;
  const showResults = status === "completed" && generated;

  /* ------------------------------- render ------------------------------- */

  return (
    <div className="gen-page">
      <div className="page-content">
        <div className="page-header">
          <p className="page-header__label">AI-Powered</p>
          <h1 className="page-header__title">Content Generation</h1>
          <p className="page-header__subtitle">
            Upload your inventory and let GLM build your entire ad strategy.
          </p>
        </div>

        <StepIndicator steps={STEPS} currentStep={indicatorStep} />

        <ErrorBanner
          error={validationError ? { message: validationError } : error}
          onDismiss={validationError ? () => {
            setValidationError(null);
            setUploadedFile(null);
            setCsvPreview({ columns: [], rows: [], totalRows: 0, missingColumns: [] });
            if (fileInputRef.current) fileInputRef.current.value = "";
          } : dismissError}
          onRetry={
            !validationError && ((isPhaseAError && uploadedFile) || isPhaseBError)
              ? handleRetry
              : null
          }
          retryLabel={isPhaseBError ? "Retry generation" : "Re-analyse"}
        />

        {/* RUNNING — shared timeline view for both phases */}
        {showRunningTimeline && (
          <div className="gen-step gen-step--timeline">
            <PipelineTimeline
              currentStepIndex={currentStepIndex}
              status={status}
              startedAt={startedAt}
              campaignLabel={campaignLabel}
              area={jobArea}
            />
            <div className="gen-step-actions gen-step-actions--split">
              <button className="btn btn-ghost" onClick={handleReset}>
                Cancel campaign
              </button>
              <span className="gen-running-cta">
                Running in the background — feel free to navigate around.
              </span>
            </div>
          </div>
        )}

        {/* STEP 1 — Upload */}
        {showUploadStep && !showRunningTimeline && (
          <div className="gen-step gen-step--upload">
            <div className="gen-section-header">
              <h2>Upload Product Inventory</h2>
              <p>
                Upload a CSV or Excel file (.xlsx, .xls) with your product names, stock levels,
                categories, and pricing. GLM will read and analyse your data.
              </p>
            </div>

            <div
              className={`gen-dropzone ${dragOver ? "gen-dropzone--over" : ""} ${uploadedFile ? "gen-dropzone--filled" : ""}`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleFileDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.xlsx,.xls"
                style={{ display: "none" }}
                onChange={handleFileSelect}
              />
              <div className="gen-dropzone__icon">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                >
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              {uploadedFile ? (
                <div className="gen-dropzone__file-info">
                  <span className="gen-dropzone__filename">
                    {uploadedFile.name}
                  </span>
                  <span className="gen-dropzone__filesize">
                    {(uploadedFile.size / 1024).toFixed(1)} KB
                  </span>
                </div>
              ) : (
                <>
                  <p className="gen-dropzone__main">Drop your file here</p>
                  <p className="gen-dropzone__sub">
                    or click to browse — CSV or Excel format, max 5 MB
                  </p>
                </>
              )}
            </div>

            {isValidating && (
              <div className="gen-validation-loader">
                <div className="gen-validation-loader__text">
                  <span>Validating inventory data...</span>
                  <span>{validationProgress}%</span>
                </div>
                <div className="gen-validation-loader__bar-bg">
                  <div 
                    className="gen-validation-loader__bar-fill" 
                    style={{ width: `${validationProgress}%` }}
                  />
                </div>
              </div>
            )}

            {csvPreview.missingColumns.length > 0 && (
              <div className="gen-error-banner" style={{ marginBottom: '1.5rem', borderRadius: '12px' }}>
                <div className="gen-error-banner__head">
                  <strong>Missing Required Columns</strong>
                </div>
                <p style={{ marginTop: '0.5rem', fontSize: '0.9rem', opacity: 0.9 }}>
                  Your file is missing: {csvPreview.missingColumns.join(", ")}.
                  Please check the expected format below.
                </p>
              </div>
            )}

            <div className="gen-csv-hint">
              <div className="gen-csv-hint__label">Expected columns:</div>
              <div className="gen-csv-hint__cols">
                {REQUIRED_COLUMNS.map((c) => {
                  const isMissing = (csvPreview.missingColumns || []).includes(c);
                  return (
                    <span
                      key={c}
                      className={`gen-csv-col ${isMissing ? 'gen-csv-col--missing' : ''}`}
                      title={isMissing ? 'This column is missing from your file' : 'Correct'}
                    >
                      {c} {isMissing && '✕'}
                    </span>
                  );
                })}
                <span className="gen-csv-col gen-csv-col--optional">date_added (opt)</span>
                <span className="gen-csv-col gen-csv-col--optional">expiry_date (opt)</span>
              </div>
            </div>

            <div className="gen-area-row">
              <label htmlFor="gen-area-input" className="gen-area-label">
                Target region (optional)
              </label>
              <input
                id="gen-area-input"
                type="text"
                className="gen-area-input"
                placeholder="e.g. Kuala Lumpur — leave blank to use the backend default"
                value={areaOverride}
                onChange={(e) => setAreaOverride(e.target.value)}
              />
            </div>

            {csvPreview.rows.length > 0 && (
              <div className="gen-preview-wrap">
                <div className="gen-preview__header">
                  <span className="gen-preview__title">Inventory Preview</span>
                  <span className="gen-preview__count">
                    Showing first {csvPreview.rows.length} of{" "}
                    {csvPreview.totalRows} rows
                  </span>
                </div>
                <div className="gen-table-scroll">
                  <table className="gen-inventory-table">
                    <thead>
                      <tr>
                        {csvPreview.columns.map((c) => (
                          <th key={c}>{c}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {csvPreview.rows.map((row, i) => (
                        <tr key={i}>
                          {csvPreview.columns.map((c) => (
                            <td key={c}>{row[c]}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <div className="gen-step-actions">
              <button
                className="btn btn-primary btn-lg"
                onClick={handleAnalyse}
                disabled={!uploadedFile || !!validationError}
              >
                Analyse Inventory
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  width="16"
                  height="16"
                >
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* STEP 2 — Recommendations */}
        {showPicker && phaseAResponse && (
          <div className="gen-step">
            <div className="gen-section-header">
              <h2>GLM Recommendations</h2>
              <p>
                Based on your inventory, current trends, and the seasonal
                calendar, GLM has generated these advertising recommendations.
              </p>
            </div>

            <div className="gen-rec-context">
              {liveContext?.upcoming_events?.[0] && (
                <div className="gen-rec-context__item">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    width="16"
                    height="16"
                  >
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                    <line x1="16" y1="2" x2="16" y2="6" />
                    <line x1="8" y1="2" x2="8" y2="6" />
                    <line x1="3" y1="10" x2="21" y2="10" />
                  </svg>
                  <span>Event: {liveContext.upcoming_events[0]}</span>
                </div>
              )}
              {liveContext?.trending_formats?.length > 0 && (
                <div className="gen-rec-context__item">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    width="16"
                    height="16"
                  >
                    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                  </svg>
                  <span>
                    Trends:{" "}
                    {liveContext.trending_formats.slice(0, 2).join(", ")}
                  </span>
                </div>
              )}
              {riskCounts && (
                <div className="gen-rec-context__item">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    width="16"
                    height="16"
                  >
                    <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
                    <line x1="7" y1="7" x2="7.01" y2="7" />
                  </svg>
                  <span>
                    {riskCounts.high} high, {riskCounts.medium} medium,{" "}
                    {riskCounts.low} low risk
                  </span>
                </div>
              )}
            </div>

            <div className="gen-rec-grid">
              {recommendations.map((rec) => (
                <RecommendationCard
                  key={rec.id}
                  rec={rec}
                  selected={selectedIdx === rec.id}
                  onSelect={setSelectedIdx}
                />
              ))}
            </div>

            <div className="gen-step-actions gen-step-actions--split">
              <button className="btn btn-ghost" onClick={handleReset}>
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  width="14"
                  height="14"
                >
                  <line x1="19" y1="12" x2="5" y2="12" />
                  <polyline points="12 19 5 12 12 5" />
                </svg>
                Start Over
              </button>
              <button
                className="btn btn-primary btn-lg"
                onClick={handleProceed}
                disabled={selectedIdx == null}
              >
                Proceed with Selection
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  width="16"
                  height="16"
                >
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* STEP 3 — Review */}
        {showReview &&
          phaseAResponse &&
          selectedIdx != null &&
          (() => {
            const rec = recommendations.find((r) => r.id === selectedIdx);
            const opt = phaseAResponse.strategies[selectedIdx];
            if (!rec || !opt) return null;
            return (
              <div className="gen-step">
                <div className="gen-section-header">
                  <h2>Review Your Selection</h2>
                  <p>
                    You have selected the following recommendation. Review the
                    details before generating your ad content.
                  </p>
                </div>

                <div className="gen-review-card">
                  <div className="gen-review-card__main">
                    <div className="gen-review-card__header">
                      <div>
                        <span className="gen-review-badge">{rec.platform}</span>
                        <span className="gen-review-badge gen-review-badge--format">
                          {rec.format}
                        </span>
                      </div>
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => setReviewMode(false)}
                      >
                        Change
                      </button>
                    </div>

                    <h3 className="gen-review-card__product">{rec.product}</h3>

                    <div className="gen-review-reason">
                      <span className="gen-review-reason__label">
                        Why GLM recommends this
                      </span>
                      <p>{rec.reason}</p>
                    </div>
                  </div>

                  <div className="gen-review-card__sidebar">
                    <div className="gen-review-details">
                      {[
                        { label: "Target Audience", value: rec.audience },
                        { label: "Pricing Strategy", value: rec.pricing },
                        { label: "Best Time to Post", value: rec.bestTime },
                        { label: "Budget", value: opt.strategy.budget },
                        {
                          label: "Predicted Reach",
                          value: `${opt.strategy.predicted_reach.toLocaleString()} people`,
                        },
                        {
                          label: "Predicted ROI",
                          value: opt.strategy.predicted_roi,
                        },
                        {
                          label: "Unit Price",
                          value: `RM ${opt.unit_price_rm.toFixed(2)}`,
                        },
                      ].map((d) => (
                        <div key={d.label} className="gen-review-detail">
                          <span className="gen-review-detail__label">
                            {d.label}
                          </span>
                          <span className="gen-review-detail__value">
                            {d.value}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="gen-step-actions gen-step-actions--split">
                  <button
                    className="btn btn-ghost"
                    onClick={() => setReviewMode(false)}
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      width="14"
                      height="14"
                    >
                      <line x1="19" y1="12" x2="5" y2="12" />
                      <polyline points="12 19 5 12 12 5" />
                    </svg>
                    Back
                  </button>
                  <button
                    className="btn btn-primary btn-lg"
                    onClick={handleGenerate}
                  >
                    Generate Ad Content
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      width="16"
                      height="16"
                    >
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                    </svg>
                  </button>
                </div>
              </div>
            );
          })()}

        {/* STEP 4 — Generated Content */}
        {showResults && (
          <div className="gen-step">
            <div className="gen-section-header">
              <h2>Your Ad Content is Ready</h2>
              <p>
                GLM has generated complete, trend-informed ad content for your
                campaign. Copy and use directly.
              </p>
            </div>

            <div className="gen-output-grid">
              {generated.image && (
                <div className="gen-output-card gen-output-card--image">
                  <div className="gen-output-card__header">
                    <span className="gen-output-card__label">
                      Generated Image
                    </span>
                    <a
                      className="gen-copy-btn"
                      href={generated.image}
                      download={`ad-${generated.product || "image"}.png`}
                    >
                      Download
                    </a>
                  </div>
                  <img
                    src={generated.image}
                    alt={`Generated ad for ${generated.product}`}
                    className="gen-output-image"
                  />
                  {generated.imagePrompt && (
                    <p className="gen-output-card__caption-muted">
                      Prompt: {generated.imagePrompt}
                    </p>
                  )}
                </div>
              )}

              <div className="gen-output-card">
                <div className="gen-output-card__header">
                  <span className="gen-output-card__label">Ad Copy</span>
                  <button
                    className="gen-copy-btn"
                    onClick={() => copyToClipboard(generated.adCopy, "copy")}
                  >
                    {copiedField === "copy" ? (
                      "Copied!"
                    ) : (
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        width="16"
                        height="16"
                      >
                        <rect
                          x="9"
                          y="9"
                          width="13"
                          height="13"
                          rx="2"
                          ry="2"
                        />
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                      </svg>
                    )}
                  </button>
                </div>
                <pre className="gen-output-card__text">{generated.adCopy}</pre>
              </div>

              <div className="gen-output-card gen-output-card--captions">
                <div className="gen-output-card__header">
                  <span className="gen-output-card__label">
                    Caption Options
                  </span>
                </div>
                <div className="gen-captions">
                  {generated.captions.map((cap, i) => (
                    <div key={i} className="gen-caption-item">
                      <span className="gen-caption-item__num">
                        Option {i + 1}
                      </span>
                      <p>{cap}</p>
                      <button
                        className="gen-copy-btn"
                        onClick={() => copyToClipboard(cap, `cap-${i}`)}
                      >
                        {copiedField === `cap-${i}` ? "Copied!" : "Copy"}
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="gen-output-card gen-output-card--hashtags">
                <div className="gen-output-card__header">
                  <span className="gen-output-card__label">Hashtags</span>
                  <button
                    className="gen-copy-btn"
                    onClick={() =>
                      copyToClipboard(generated.hashtags.join(" "), "hashtags")
                    }
                  >
                    {copiedField === "hashtags" ? "Copied!" : "Copy All"}
                  </button>
                </div>
                <div className="gen-hashtags">
                  {generated.hashtags.map((h) => (
                    <span key={h} className="gen-hashtag">
                      {h}
                    </span>
                  ))}
                </div>
              </div>

              {generated.explanation?.platform_choice && (
                <div className="gen-output-card gen-output-card--guide">
                  <div className="gen-output-card__header">
                    <span className="gen-output-card__label">
                      Why {generated.explanation.platform_choice.platform}?
                    </span>
                    <div className="gen-output-badges">
                      <span className="badge badge--success">
                        {generated.platform}
                      </span>
                      <span className="badge badge--pending">
                        {generated.format}
                      </span>
                    </div>
                  </div>
                  <ul className="gen-output-list">
                    {generated.explanation.platform_choice.reasons.map(
                      (r, i) => (
                        <li key={i}>{r}</li>
                      ),
                    )}
                  </ul>
                </div>
              )}

              {generated.explanation?.financial_projection && (
                <div className="gen-output-card gen-output-card--guide">
                  <div className="gen-output-card__header">
                    <span className="gen-output-card__label">
                      Financial Projection
                    </span>
                  </div>
                  <div className="gen-finance-grid">
                    {[
                      [
                        "Spend",
                        `RM ${generated.explanation.financial_projection.spend_rm.toFixed(0)}`,
                      ],
                      [
                        "Reach",
                        generated.explanation.financial_projection.predicted_reach.toLocaleString(),
                      ],
                      [
                        "Clicks",
                        generated.explanation.financial_projection.predicted_clicks.toLocaleString(),
                      ],
                      [
                        "Sales",
                        generated.explanation.financial_projection.predicted_sales.toLocaleString(),
                      ],
                      [
                        "Revenue",
                        `RM ${generated.explanation.financial_projection.predicted_revenue_rm.toFixed(0)}`,
                      ],
                      [
                        "ROI",
                        `${generated.explanation.financial_projection.roi_percent.toFixed(0)}%`,
                      ],
                    ].map(([label, value]) => (
                      <div key={label} className="gen-finance-cell">
                        <span className="gen-finance-cell__label">{label}</span>
                        <span className="gen-finance-cell__value">{value}</span>
                      </div>
                    ))}
                  </div>
                  <p className="gen-output-card__text gen-finance-summary">
                    {generated.explanation.financial_projection.summary_line}
                  </p>
                </div>
              )}

              {generated.explanation?.risk_vs_reward && (
                <div className="gen-output-card gen-output-card--guide">
                  <div className="gen-output-card__header">
                    <span className="gen-output-card__label">
                      Risks vs Rewards
                    </span>
                  </div>
                  <div className="gen-risk-reward">
                    <div>
                      <span className="gen-risk-reward__label gen-risk-reward__label--risk">
                        Risks
                      </span>
                      <ul className="gen-output-list">
                        {generated.explanation.risk_vs_reward.risks.map(
                          (r, i) => (
                            <li key={i}>{r}</li>
                          ),
                        )}
                      </ul>
                    </div>
                    <div>
                      <span className="gen-risk-reward__label gen-risk-reward__label--reward">
                        Rewards
                      </span>
                      <ul className="gen-output-list">
                        {generated.explanation.risk_vs_reward.rewards.map(
                          (r, i) => (
                            <li key={i}>{r}</li>
                          ),
                        )}
                      </ul>
                    </div>
                  </div>
                  {generated.explanation.risk_vs_reward.verdict && (
                    <p className="gen-output-card__text gen-finance-summary">
                      <strong>Verdict:</strong>{" "}
                      {generated.explanation.risk_vs_reward.verdict}
                    </p>
                  )}
                </div>
              )}
            </div>

            <div className="gen-step-actions gen-step-actions--split">
              <button className="btn btn-ghost" onClick={handleReset}>
                Start New Campaign
              </button>
              <button
                className="btn btn-secondary"
                onClick={() =>
                  copyToClipboard(JSON.stringify(finalResult, null, 2), "json")
                }
              >
                {copiedField === "json" ? (
                  "Copied!"
                ) : (
                  <>
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      width="16"
                      height="16"
                    >
                      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
                      <polyline points="17 21 17 13 7 13 7 21" />
                      <polyline points="7 3 7 8 15 8" />
                    </svg>
                    Copy Raw JSON
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
