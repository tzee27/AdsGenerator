/**
 * Tiny localStorage-backed history of generated ads.
 *
 * No backend persistence yet, so this lives client-side. Each entry is a
 * normalised "card" + the full Phase B response so the modal can show
 * everything (variants, image, explanation) on demand.
 */

const STORAGE_KEY = 'adsgen.history.v1';
const MAX_ENTRIES = 50;

function readAll() {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeAll(entries) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(entries.slice(0, MAX_ENTRIES)));
  } catch {
    // Quota exceeded or storage disabled — fail silently.
  }
}

function pickFirstVariant(variants) {
  return Array.isArray(variants) && variants.length > 0 ? variants[0] : null;
}

/**
 * Normalise a successful Phase B run into something AdCard / the Main modal
 * can render directly. We deliberately keep the original payload too so the
 * detail view can dig into multi-variant copy + the explanation.
 */
function buildEntry({ phaseAResponse, selectedStrategy, finalizeResponse }) {
  const variant = pickFirstVariant(finalizeResponse?.content?.content_variants);
  const image = finalizeResponse?.content?.image;
  const product = selectedStrategy?.featured_product;
  const strategy = selectedStrategy?.strategy;

  const captionShort = variant?.caption || strategy?.angle || product?.product || 'Generated ad';

  return {
    id: `gen-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    createdAt: new Date().toISOString(),
    platform: strategy?.platform || 'TikTok',
    format: strategy?.format || 'Image',
    category: product?.category || finalizeResponse?.metadata?.featured_product?.category || 'General',
    productName: product?.product || 'Featured product',
    caption: captionShort,
    fullCaption: variant?.caption || captionShort,
    headline: variant?.headline || '',
    callToAction: variant?.call_to_action || '',
    hashtags: Array.isArray(variant?.hashtags) ? variant.hashtags : [],
    audience: strategy?.audience || '',
    bestTime: strategy?.timing || '',
    pricing: strategy?.pricing || '',
    budget: strategy?.budget || '',
    angle: strategy?.angle || '',
    rationale: selectedStrategy?.rationale || '',
    image: image
      ? { mimeType: image.mime_type, base64: image.base64 }
      : null,
    variants: finalizeResponse?.content?.content_variants || [],
    explanation: finalizeResponse?.explanation || null,
    metadata: finalizeResponse?.metadata || null,
    riskAnalysis: phaseAResponse?.risk_analysis || null,
    liveContext: phaseAResponse?.live_context || null,
  };
}

export function listHistory() {
  return readAll();
}

export function saveGeneratedAd(payload) {
  const entry = buildEntry(payload);
  const next = [entry, ...readAll().filter((e) => e.id !== entry.id)];
  writeAll(next);
  return entry;
}

export function clearHistory() {
  writeAll([]);
}

export function deleteHistoryEntry(id) {
  writeAll(readAll().filter((e) => e.id !== id));
}
