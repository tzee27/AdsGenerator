/**
 * Tiny localStorage-backed history of generated ads.
 *
 * No backend persistence yet, so this lives client-side. Each entry is a
 * normalised "card" + the full Phase B response so the modal can show
 * everything (variants, image, explanation) on demand.
 */

import { collection, addDoc, getDocs, deleteDoc, doc, query, orderBy } from 'firebase/firestore';
import { db } from './firebase';

const MAX_ENTRIES = 50;

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
    image: image?.url || (image?.base64
      ? { mimeType: image.mime_type, base64: image.base64 }
      : null),
    variants: finalizeResponse?.content?.content_variants || [],
    explanation: finalizeResponse?.explanation || null,
    metadata: finalizeResponse?.metadata || null,
    riskAnalysis: phaseAResponse?.risk_analysis || null,
    liveContext: phaseAResponse?.live_context || null,
  };
}

export async function listHistory(userId) {
  if (!userId) return [];
  try {
    const q = query(collection(db, 'users', userId, 'savedAds'), orderBy('createdAt', 'desc'));
    const snapshot = await getDocs(q);
    return snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
  } catch (e) {
    console.error("Failed to fetch history:", e);
    return [];
  }
}

export async function saveGeneratedAd(userId, payload) {
  if (!userId) throw new Error("User ID is required to save an ad.");
  const entry = buildEntry(payload);
  
  // Remove the temporary ID, let Firestore generate one
  const { id, ...dataToSave } = entry;
  
  try {
    const docRef = await addDoc(collection(db, 'users', userId, 'savedAds'), dataToSave);
    return { id: docRef.id, ...dataToSave };
  } catch (e) {
    console.error("Failed to save ad:", e);
    throw e;
  }
}

export async function deleteHistoryEntry(userId, adId) {
  if (!userId || !adId) return;
  try {
    await deleteDoc(doc(db, 'users', userId, 'savedAds', adId));
  } catch (e) {
    console.error("Failed to delete ad:", e);
  }
}
