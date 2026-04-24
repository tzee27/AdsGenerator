import { useState, useRef } from 'react';
import StepIndicator from '../components/StepIndicator';
import RecommendationCard from '../components/RecommendationCard';
import '../styles/ContentGeneration.css';

const STEPS = ['Upload Inventory', 'AI Recommendations', 'Review & Select', 'Generated Content'];

const MOCK_INVENTORY = [
  { name: 'Bamboo Linen Set (Queen)', stock: 45, category: 'Home & Living', price: 'RM 189' },
  { name: 'Vitamin C Serum 30ml', stock: 12, category: 'Skincare', price: 'RM 58' },
  { name: 'Wireless Earbuds Pro', stock: 8, category: 'Electronics', price: 'RM 129' },
  { name: 'Organic Cotton Onesie', stock: 67, category: 'Baby & Kids', price: 'RM 39' },
  { name: 'Resistance Band Set', stock: 30, category: 'Sports & Fitness', price: 'RM 55' },
];

const MOCK_RECOMMENDATIONS = [
  {
    id: 1,
    platform: 'TikTok',
    format: 'Video',
    product: 'Vitamin C Serum 30ml',
    audience: 'Women 22–35, skincare enthusiasts, urban lifestyle',
    pricing: 'Bundle with toner — offer "Glow Duo" at RM89 (save RM27)',
    bestTime: 'Thursday–Friday, 8–10 PM',
    reason: 'Low stock (12 units) triggers urgency. TikTok skincare trend peaking this week — "glass skin" is viral. Hari Raya prep window creates high demand for glow products.',
  },
  {
    id: 2,
    platform: 'Shopee',
    format: 'Image',
    product: 'Bamboo Linen Set (Queen)',
    audience: 'Married women 28–45, homemakers, new homeowners',
    pricing: 'Raya Home Refresh promo — 15% off + free pillowcase gift',
    bestTime: 'Saturday morning, 9–11 AM (peak Shopee browsing)',
    reason: 'High stock (45 units) needs movement before Raya season ends. Home category always spikes in March–April. Image format works well for Shopee banners.',
  },
  {
    id: 3,
    platform: 'Instagram',
    format: 'Image',
    product: 'Wireless Earbuds Pro',
    audience: 'Tech-savvy men 20–32, students and remote workers',
    pricing: 'Flash deal — RM99 for 48 hours (save RM30)',
    bestTime: 'Sunday evening, 7–9 PM',
    reason: 'Only 8 units left — scarcity drives conversions. Instagram Stories with countdown timer + limited-stock copy performs well for electronics flash sales.',
  },
];

const MOCK_GENERATED = {
  platform: 'TikTok',
  format: 'Video',
  product: 'Vitamin C Serum 30ml',
  adCopy: `✨ Only 12 left — and they\'re going FAST.\n\nMeet your new glow secret: our Vitamin C Serum.\nDermatologist-tested. Packed with 15% pure ascorbic acid.\nSee results in 14 days or your money back.\n\n🔥 Raya Glow Deal: Grab the Glow Duo for RM89 (was RM116)\nFree shipping • Ships in 1 day • Secure checkout`,
  captions: [
    'She asked what my skincare secret was. I showed her this. #GlassSkin #VitaminCSerum #RayaGlow #SkincareRoutine #MalaysiaBeauty',
    'POV: You found the best vitamin C serum under RM60 and now your skin is obsessed. Link in bio! #SkincareTikTok #GlowUp',
  ],
  hashtags: ['#VitaminC', '#GlassSkin', '#SkincareRoutine', '#RayaGlow', '#MalaysiaBeauty', '#SkincareTok', '#GlowUp', '#BeautyHacks', '#HariRaya2025'],
  postingGuide: 'Post as a TikTok "Get Ready With Me" or "Skincare Routine" video. Show before/after results in the first 3 seconds to hook viewers. Use TikTok\'s auto-caption feature. Pin the bundle offer in your first comment. Post at 9 PM Thursday for maximum reach.',
};

export default function ContentGeneration() {
  const [step, setStep] = useState(1);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [isAnalysing, setIsAnalysing] = useState(false);
  const [selectedRec, setSelectedRec] = useState(null);
  const [copiedField, setCopiedField] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) setUploadedFile(file);
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) setUploadedFile(file);
  };

  const handleAnalyse = () => {
    setIsAnalysing(true);
    setTimeout(() => {
      setIsAnalysing(false);
      setStep(2);
    }, 2000);
  };

  const handleProceed = () => {
    if (selectedRec) setStep(3);
  };

  const handleGenerate = () => {
    setIsAnalysing(true);
    setTimeout(() => {
      setIsAnalysing(false);
      setStep(4);
    }, 2200);
  };

  const copyToClipboard = (text, field) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    });
  };

  return (
    <div className="gen-page">
      <div className="page-content">
        <div className="page-header">
          <p className="page-header__label">AI-Powered</p>
          <h1 className="page-header__title">Content Generation</h1>
          <p className="page-header__subtitle">Upload your inventory and let GLM build your entire ad strategy.</p>
        </div>

        <StepIndicator steps={STEPS} currentStep={step} />

        {/* STEP 1 — Upload */}
        {step === 1 && (
          <div className="gen-step gen-step--upload">
            <div className="gen-section-header">
              <h2>Upload Product Inventory</h2>
              <p>Upload a CSV file with your product names, stock levels, categories, and pricing. GLM will read and analyse your data.</p>
            </div>

            <div
              className={`gen-dropzone ${dragOver ? 'gen-dropzone--over' : ''} ${uploadedFile ? 'gen-dropzone--filled' : ''}`}
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleFileDrop}
              onClick={() => fileInputRef.current.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                style={{ display: 'none' }}
                onChange={handleFileSelect}
              />
              <div className="gen-dropzone__icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              {uploadedFile ? (
                <div className="gen-dropzone__file-info">
                  <span className="gen-dropzone__filename">{uploadedFile.name}</span>
                  <span className="gen-dropzone__filesize">{(uploadedFile.size / 1024).toFixed(1)} KB</span>
                </div>
              ) : (
                <>
                  <p className="gen-dropzone__main">Drop your CSV file here</p>
                  <p className="gen-dropzone__sub">or click to browse — CSV format, max 10MB</p>
                </>
              )}
            </div>

            {/* CSV format hint */}
            <div className="gen-csv-hint">
              <div className="gen-csv-hint__label">Expected columns:</div>
              <div className="gen-csv-hint__cols">
                {['product_name', 'stock_quantity', 'category', 'price', 'sku (optional)'].map(c => (
                  <span key={c} className="gen-csv-col">{c}</span>
                ))}
              </div>
            </div>

            {/* Preview list — redesigned for clarity */}
            <div className="gen-preview">
              <div className="gen-preview__header">
                <span className="gen-preview__title">Inventory Preview</span>
                <span className="gen-preview__count">{MOCK_INVENTORY.length} products</span>
              </div>
              <div className="gen-inventory-list">
                {MOCK_INVENTORY.map((item, i) => (
                  <div key={i} className="gen-inventory-item">
                    <div className="gen-inventory-item__info">
                      <span className="gen-inventory-item__name">{item.name}</span>
                      <span className="gen-inventory-item__category">{item.category}</span>
                    </div>
                    <div className="gen-inventory-item__meta">
                      <div className="gen-inventory-item__stock">
                        <span className="gen-inventory-item__label">Stock</span>
                        <span className={`gen-stock-badge ${item.stock < 15 ? 'gen-stock-badge--low' : ''}`}>
                          {item.stock} units
                        </span>
                      </div>
                      <div className="gen-inventory-item__price">
                        <span className="gen-inventory-item__label">Price</span>
                        <span className="gen-inventory-item__value">{item.price}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="gen-step-actions">
              <button
                className="btn btn-primary btn-lg"
                onClick={handleAnalyse}
                disabled={isAnalysing}
              >
                {isAnalysing ? (
                  <>
                    <span className="gen-spinner" />
                    Analysing with GLM...
                  </>
                ) : (
                  <>
                    Analyse Inventory
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                    </svg>
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* STEP 2 — Recommendations */}
        {step === 2 && (
          <div className="gen-step">
            <div className="gen-section-header">
              <h2>GLM Recommendations</h2>
              <p>Based on your inventory, current trends, and the seasonal calendar, GLM has generated these advertising recommendations.</p>
            </div>

            <div className="gen-rec-context">
              <div className="gen-rec-context__item">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" width="16" height="16">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
                <span>Season: Hari Raya Aidilfitri 2025</span>
              </div>
              <div className="gen-rec-context__item">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" width="16" height="16">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                </svg>
                <span>Trend: Glass skin, home refresh, ramadan prep</span>
              </div>
              <div className="gen-rec-context__item">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" width="16" height="16">
                  <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
                  <line x1="7" y1="7" x2="7.01" y2="7" />
                </svg>
                <span>5 products analysed — 3 flagged for promotion</span>
              </div>
            </div>

            <div className="gen-rec-grid">
              {MOCK_RECOMMENDATIONS.map(rec => (
                <RecommendationCard
                  key={rec.id}
                  rec={rec}
                  selected={selectedRec === rec.id}
                  onSelect={setSelectedRec}
                />
              ))}
            </div>

            <div className="gen-step-actions gen-step-actions--split">
              <button className="btn btn-ghost" onClick={() => setStep(1)}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
                  <line x1="19" y1="12" x2="5" y2="12" />
                  <polyline points="12 19 5 12 12 5" />
                </svg>
                Back
              </button>
              <button
                className="btn btn-primary btn-lg"
                onClick={handleProceed}
                disabled={!selectedRec}
              >
                Proceed with Selection
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* STEP 3 — Review */}
        {step === 3 && (
          <div className="gen-step">
            <div className="gen-section-header">
              <h2>Review Your Selection</h2>
              <p>You have selected the following recommendation. Review the details before generating your ad content.</p>
            </div>

            {selectedRec && (() => {
              const rec = MOCK_RECOMMENDATIONS.find(r => r.id === selectedRec);
              return (
                <div className="gen-review-card">
                  <div className="gen-review-card__header">
                    <div>
                      <span className="gen-review-badge">{rec.platform}</span>
                      <span className="gen-review-badge gen-review-badge--format">{rec.format}</span>
                    </div>
                    <button className="btn btn-ghost btn-sm" onClick={() => setStep(2)}>Change</button>
                  </div>

                  <h3 className="gen-review-card__product">{rec.product}</h3>

                  <div className="gen-review-details">
                    {[
                      { label: 'Target Audience', value: rec.audience },
                      { label: 'Pricing Strategy', value: rec.pricing },
                      { label: 'Best Time to Post', value: rec.bestTime },
                    ].map(d => (
                      <div key={d.label} className="gen-review-detail">
                        <span className="gen-review-detail__label">{d.label}</span>
                        <span className="gen-review-detail__value">{d.value}</span>
                      </div>
                    ))}
                  </div>

                  <div className="gen-review-reason">
                    <span className="gen-review-reason__label">Why GLM recommends this</span>
                    <p>{rec.reason}</p>
                  </div>
                </div>
              );
            })()}

            <div className="gen-step-actions gen-step-actions--split">
              <button className="btn btn-ghost" onClick={() => setStep(2)}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
                  <line x1="19" y1="12" x2="5" y2="12" />
                  <polyline points="12 19 5 12 12 5" />
                </svg>
                Back
              </button>
              <button className="btn btn-primary btn-lg" onClick={handleGenerate} disabled={isAnalysing}>
                {isAnalysing ? (
                  <>
                    <span className="gen-spinner" />
                    Generating Content...
                  </>
                ) : (
                  <>
                    Generate Ad Content
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                    </svg>
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* STEP 4 — Generated Content */}
        {step === 4 && (
          <div className="gen-step">
            <div className="gen-section-header">
              <h2>Your Ad Content is Ready</h2>
              <p>GLM has generated complete, trend-informed ad content for your campaign. Copy and use directly.</p>
            </div>

            <div className="gen-output-grid">
              {/* Ad Copy */}
              <div className="gen-output-card">
                <div className="gen-output-card__header">
                  <span className="gen-output-card__label">Ad Copy</span>
                  <button
                    className="gen-copy-btn"
                    onClick={() => copyToClipboard(MOCK_GENERATED.adCopy, 'copy')}
                  >
                    {copiedField === 'copy' ? 'Copied!' : (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" width="16" height="16">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                      </svg>
                    )}
                  </button>
                </div>
                <pre className="gen-output-card__text">{MOCK_GENERATED.adCopy}</pre>
              </div>

              {/* Captions */}
              <div className="gen-output-card">
                <div className="gen-output-card__header">
                  <span className="gen-output-card__label">Caption Options</span>
                </div>
                <div className="gen-captions">
                  {MOCK_GENERATED.captions.map((cap, i) => (
                    <div key={i} className="gen-caption-item">
                      <span className="gen-caption-item__num">Option {i + 1}</span>
                      <p>{cap}</p>
                      <button
                        className="gen-copy-btn"
                        onClick={() => copyToClipboard(cap, `cap-${i}`)}
                      >
                        {copiedField === `cap-${i}` ? 'Copied!' : 'Copy'}
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Hashtags */}
              <div className="gen-output-card">
                <div className="gen-output-card__header">
                  <span className="gen-output-card__label">Hashtags</span>
                  <button
                    className="gen-copy-btn"
                    onClick={() => copyToClipboard(MOCK_GENERATED.hashtags.join(' '), 'hashtags')}
                  >
                    {copiedField === 'hashtags' ? 'Copied!' : 'Copy All'}
                  </button>
                </div>
                <div className="gen-hashtags">
                  {MOCK_GENERATED.hashtags.map(h => (
                    <span key={h} className="gen-hashtag">{h}</span>
                  ))}
                </div>
              </div>

              {/* Posting Guide */}
              <div className="gen-output-card gen-output-card--guide">
                <div className="gen-output-card__header">
                  <span className="gen-output-card__label">Posting Guide</span>
                  <div className="gen-output-badges">
                    <span className="badge badge--success">{MOCK_GENERATED.platform}</span>
                    <span className="badge badge--pending">{MOCK_GENERATED.format}</span>
                  </div>
                </div>
                <p className="gen-output-card__text">{MOCK_GENERATED.postingGuide}</p>
              </div>
            </div>

            <div className="gen-step-actions gen-step-actions--split">
              <button className="btn btn-ghost" onClick={() => { setStep(1); setSelectedRec(null); setUploadedFile(null); }}>
                Start New Campaign
              </button>
              <button className="btn btn-secondary" onClick={() => {}}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" width="16" height="16">
                  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
                  <polyline points="17 21 17 13 7 13 7 21" />
                  <polyline points="7 3 7 8 15 8" />
                </svg>
                Save to History
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
