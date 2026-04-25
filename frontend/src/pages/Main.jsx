import { useEffect, useMemo, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import AdCard from '../components/AdCard';
import { deleteHistoryEntry, listHistory } from '../lib/history';
import '../styles/Main.css';

const ALL_PLATFORMS = ['All', 'TikTok', 'Shopee', 'Instagram', 'Facebook', 'Lazada'];
const ALL_FORMATS = ['All', 'Video', 'Image', 'Text'];



function platformClass(p) {
  return (p || '').toLowerCase().replace(/[^a-z]/g, '');
}

function formatRelativeDate(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, {
      day: '2-digit', month: 'short', year: 'numeric',
    });
  } catch {
    return iso;
  }
}

/** Normalise a history entry into the shape the modal/card expect. */
function liveEntryToAd(entry) {
  return {
    id: entry.id,
    isLive: entry.isLive || false,
    platform: entry.platform,
    format: entry.format,
    category: entry.category,
    caption: entry.caption,
    fullCaption: entry.fullCaption,
    headline: entry.headline,
    callToAction: entry.callToAction,
    hashtags: entry.hashtags || [],
    audience: entry.audience,
    bestTime: entry.bestTime,
    pricing: entry.pricing,
    budget: entry.budget,
    angle: entry.angle,
    rationale: entry.rationale,
    image: entry.image
      ? (typeof entry.image === 'string' ? entry.image : `data:${entry.image.mimeType};base64,${entry.image.base64}`)
      : null,
    date: formatRelativeDate(entry.createdAt),
    explanation: entry.explanation,
    metadata: entry.metadata,
    productName: entry.productName,
  };
}

function normaliseFormat(format) {
  if (!format) return 'Image';
  const lc = format.toLowerCase();
  if (lc.includes('video') || lc.includes('reel') || lc.includes('story')) return 'Video';
  if (lc.includes('text')) return 'Text';
  return 'Image';
}

export default function Main() {
  const navigate = useNavigate();
  const { currentUser } = useAuth();
  
  const [activePlatform, setActivePlatform] = useState('All');
  const [activeFormat, setActiveFormat] = useState('All');
  const [selectedAd, setSelectedAd] = useState(null);
  const [liveAds, setLiveAds] = useState([]);
  const [copied, setCopied] = useState(false);

  const loadHistory = useCallback(async () => {
    if (currentUser) {
      const ads = await listHistory(currentUser.uid);
      setLiveAds(ads.map(liveEntryToAd));
    } else {
      setLiveAds([]);
    }
  }, [currentUser]);

  // Re-read history when the window regains focus or user changes
  useEffect(() => {
    loadHistory();
    const onFocus = () => loadHistory();
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [loadHistory]);

  const allAds = useMemo(() => {
    return liveAds;
  }, [liveAds]);

  const filtered = allAds.filter((ad) => {
    const platformMatch = activePlatform === 'All' || ad.platform === activePlatform;
    const formatMatch = activeFormat === 'All' || normaliseFormat(ad.format) === activeFormat;
    return platformMatch && formatMatch;
  });

  const handleDelete = async (id) => {
    if (!id?.startsWith?.('gen-')) return;
    if (currentUser) {
      await deleteHistoryEntry(currentUser.uid, id);
      setSelectedAd(null);
      loadHistory();
    }
  };

  const handleCopyAll = (ad) => {
    const blob = [
      ad.fullCaption,
      ad.hashtags?.length ? ad.hashtags.join(' ') : null,
    ].filter(Boolean).join('\n\n');
    if (!navigator?.clipboard?.writeText) return;
    navigator.clipboard.writeText(blob).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  };

  return (
    <div className="main-page">
      <div className="page-content">
        <div className="page-header">
          <p className="page-header__label">Ad Samples</p>
          <h1 className="page-header__title">Content Library</h1>
          <p className="page-header__subtitle">
            {liveAds.length > 0
              ? `${liveAds.length} campaign${liveAds.length === 1 ? '' : 's'} saved to your database.`
              : 'Browse AI-generated ad examples across platforms and formats.'}
          </p>
        </div>

        <div className="main-filters">
          <div className="main-filter-row">
            <span className="main-filter-label">Platform</span>
            <div className="main-filter-chips">
              {ALL_PLATFORMS.map((p) => (
                <button
                  key={p}
                  className={`main-chip ${activePlatform === p ? 'main-chip--active' : ''}`}
                  onClick={() => setActivePlatform(p)}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          <div className="main-filter-row">
            <span className="main-filter-label">Format</span>
            <div className="main-filter-chips">
              {ALL_FORMATS.map((f) => (
                <button
                  key={f}
                  className={`main-chip ${activeFormat === f ? 'main-chip--active' : ''}`}
                  onClick={() => setActiveFormat(f)}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          <div className="main-filter-divider" />
          <div className="main-filter-result-count">
            {filtered.length} result{filtered.length !== 1 ? 's' : ''}
          </div>
        </div>

        <div className="main-ad-grid">
          {filtered.map((ad) => (
            <AdCard key={ad.id} {...ad} onClick={() => setSelectedAd(ad)} />
          ))}
        </div>

        {filtered.length === 0 && (
          <div className="main-empty">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" width="40" height="40">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
              <line x1="8" y1="21" x2="16" y2="21" />
              <line x1="12" y1="17" x2="12" y2="21" />
            </svg>
            <p>No samples match the selected filters.</p>
          </div>
        )}
      </div>

      {selectedAd && (
        <div className="ad-modal-overlay" onClick={() => setSelectedAd(null)}>
          <div className="ad-modal" onClick={(e) => e.stopPropagation()}>
            <div className="ad-modal__header">
              <div className="ad-modal__header-left">
                <span className={`ad-modal__platform-tag platform--${platformClass(selectedAd.platform)}`}>
                  {selectedAd.platform}
                </span>
                <div className="ad-modal__header-titles">
                  <h2>
                    {selectedAd.productName || `${selectedAd.category} Campaign`}
                    {selectedAd.isLive && <span className="ad-modal__live-pill">LIVE</span>}
                  </h2>
                  <p>{selectedAd.format} format • {selectedAd.date}</p>
                </div>
              </div>
              <button
                className="ad-modal__close-circle"
                onClick={() => setSelectedAd(null)}
                aria-label="Close"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="20" height="20">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <div className="ad-modal__divider-line" />

            <div className="ad-modal__body">
              <div className="ad-modal__preview-premium">
                {selectedAd.image ? (
                  <img src={selectedAd.image} alt={selectedAd.productName} className="ad-modal__preview-image" />
                ) : (
                  <>
                    <div className="ad-modal__preview-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" width="48" height="48">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                        <circle cx="8.5" cy="8.5" r="1.5" />
                        <polyline points="21 15 16 10 5 21" />
                      </svg>
                    </div>
                    <div className="ad-modal__preview-info">
                      <span className="ad-modal__preview-status">AI-GENERATED CONTENT</span>
                      <span className="ad-modal__preview-id">Ref: {selectedAd.id}</span>
                    </div>
                  </>
                )}
              </div>

              {selectedAd.headline && (
                <div className="ad-modal__section-premium">
                  <div className="ad-modal__section-header">
                    <span className="ad-modal__section-line" />
                    <span className="ad-modal__section-title">HEADLINE</span>
                  </div>
                  <div className="ad-modal__caption-box">
                    <p><strong>{selectedAd.headline}</strong></p>
                  </div>
                </div>
              )}

              <div className="ad-modal__section-premium">
                <div className="ad-modal__section-header">
                  <span className="ad-modal__section-line" />
                  <span className="ad-modal__section-title">AD CAPTION</span>
                </div>
                <div className="ad-modal__caption-box">
                  <p>{selectedAd.fullCaption}</p>
                </div>
              </div>

              {selectedAd.callToAction && (
                <div className="ad-modal__section-premium">
                  <div className="ad-modal__section-header">
                    <span className="ad-modal__section-line" />
                    <span className="ad-modal__section-title">CALL TO ACTION</span>
                  </div>
                  <div className="ad-modal__caption-box">
                    <p>{selectedAd.callToAction}</p>
                  </div>
                </div>
              )}

              <div className="ad-modal__section-premium">
                <div className="ad-modal__section-header">
                  <span className="ad-modal__section-line" />
                  <span className="ad-modal__section-title">HASHTAGS</span>
                </div>
                <div className="ad-modal__tags">
                  {(selectedAd.hashtags || []).map((h) => (
                    <span key={h} className="ad-modal__tag-pill">{h}</span>
                  ))}
                </div>
              </div>

              <div className="ad-modal__strategy-grid">
                {[
                  { label: 'Audience', val: selectedAd.audience },
                  { label: 'Timing', val: selectedAd.bestTime },
                  { label: 'Pricing', val: selectedAd.pricing },
                ].filter((d) => d.val).map((item) => (
                  <div key={item.label} className="ad-modal__strategy-item">
                    <span className="ad-modal__strategy-label">{item.label}</span>
                    <p className="ad-modal__strategy-val">{item.val}</p>
                  </div>
                ))}
              </div>

              {selectedAd.explanation?.financial_projection && (
                <div className="ad-modal__section-premium">
                  <div className="ad-modal__section-header">
                    <span className="ad-modal__section-line" />
                    <span className="ad-modal__section-title">FINANCIAL PROJECTION</span>
                  </div>
                  <div className="ad-modal__caption-box">
                    <p>{selectedAd.explanation.financial_projection.summary_line}</p>
                  </div>
                </div>
              )}
            </div>

            <div className="ad-modal__divider-line" />

            <div className="ad-modal__footer">
              {selectedAd.id && (
                <button
                  className="ad-modal__btn-secondary ad-modal__btn-danger"
                  onClick={() => handleDelete(selectedAd.id)}
                >
                  Delete from history
                </button>
              )}
              <button
                className="ad-modal__btn-secondary"
                onClick={() => handleCopyAll(selectedAd)}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
                {copied ? 'Copied!' : 'Copy Content'}
              </button>
              <button className="ad-modal__btn-primary" onClick={() => navigate('/generate')}>
                Generate Similar
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="16" height="16">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
