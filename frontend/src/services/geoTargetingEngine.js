import { db } from "../lib/firebase";
import { deleteDoc, doc, getDoc, setDoc } from "firebase/firestore";

const CACHE_COLLECTION = "geoCache";
const CACHE_TTL_HOURS = 24;

function toCacheKey(productName, storeLocation) {
  return `${productName}_${storeLocation}`.replace(/\s+/g, "_").toLowerCase();
}

function stripJsonFences(value = "") {
  return String(value)
    .replace(/```json|```/gi, "")
    .trim();
}

function extractMessageContent(response) {
  const content = response?.choices?.[0]?.message?.content;
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((part) => {
        if (typeof part === "string") return part;
        return part?.text || "";
      })
      .join("\n")
      .trim();
  }
  return "";
}

function fallbackResult(productName, productCategory, storeLocation) {
  return {
    targetZones: [],
    avoidZones: [],
    recommendedRadiusKm: 5,
    targetDemographic: {
      ageRange: "25-45",
      gender: "All",
      interests: [productCategory || "General shoppers"],
      language: "Malay",
    },
    bestPlatform: "Facebook",
    bestTiming: "Weekday evenings 7-10PM",
    adLanguage: "Malay",
    overallConfidence: "LOW",
    searchSummary: "Search unavailable at this time.",
    reasoning: `Default targeting applied for ${productName} in ${storeLocation}. Please retry for better results.`,
  };
}

export async function clearGeoTargetingCache(productName, storeLocation) {
  const cacheKey = toCacheKey(productName, storeLocation);
  const cacheRef = doc(db, CACHE_COLLECTION, cacheKey);
  await deleteDoc(cacheRef);
}

export async function getGeoTargeting(
  productName,
  productCategory,
  storeLocation,
  primaryCustomers,
  glmClient,
) {
  const cacheKey = toCacheKey(productName, storeLocation);
  const cacheRef = doc(db, CACHE_COLLECTION, cacheKey);

  try {
    const cached = await getDoc(cacheRef);
    if (cached.exists()) {
      const data = cached.data();
      const ageHours =
        (Date.now() - Number(data?.cachedAt || 0)) / (1000 * 60 * 60);
      if (ageHours < CACHE_TTL_HOURS && data?.result) {
        return { success: true, data: data.result, source: "cache" };
      }
    }
  } catch (cacheReadError) {
    console.warn(
      "Geo cache read failed, continuing with live search:",
      cacheReadError,
    );
  }

  const today = new Date().toLocaleDateString("en-MY", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  const year = new Date().getFullYear();

  const systemPrompt = `
You are a geo-targeting specialist for Malaysian retail advertising. Today's date is ${today}.

Your job is to research and decide the most effective geographic targeting for a product ad in Malaysia.

You MUST use web search to find current, real information.
Do NOT rely on your training data alone. Always web search first.

You must perform ALL of these searches before answering:

SEARCH 1: "${productName} popular demand which area Malaysia ${year}"
SEARCH 2: "demographic breakdown ${storeLocation} Malaysia population ethnicity"
SEARCH 3: "best areas to advertise ${productCategory} near ${storeLocation} Malaysia"
SEARCH 4: "who buys ${productName} Malaysia age group income level"
SEARCH 5: "best time to post ${productCategory} ads Facebook TikTok Malaysia ${year}"

After all searches are complete, return ONLY a valid JSON object.
No preamble, no markdown, no code fences, no extra text.
  `.trim();

  const userMessage = `
Determine the best geo targeting for this ad:

Product: ${productName}
Category: ${productCategory}
Seller location: ${storeLocation}
Seller's current customers: ${primaryCustomers}
Today's date: ${today}

Return this exact JSON schema:
{
  "targetZones": [{ "area": "string", "reason": "string", "confidence": 0 }],
  "avoidZones": [{ "area": "string", "reason": "string", "confidence": 0 }],
  "recommendedRadiusKm": 0,
  "targetDemographic": {
    "ageRange": "string",
    "gender": "Male / Female / All",
    "interests": ["string"],
    "language": "string"
  },
  "bestPlatform": "Facebook / TikTok / Instagram / Shopee",
  "bestTiming": "string",
  "adLanguage": "string",
  "overallConfidence": "HIGH / MEDIUM / LOW",
  "searchSummary": "string",
  "reasoning": "string"
}
  `.trim();

  try {
    const response = await glmClient.chat({
      model: "glm-5.1",
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userMessage },
      ],
      tools: [{ type: "web_search" }],
      tool_choice: "auto",
    });

    const content = extractMessageContent(response);
    const result = JSON.parse(stripJsonFences(content));

    await setDoc(cacheRef, {
      result,
      cachedAt: Date.now(),
      productName,
      storeLocation,
    });

    return { success: true, data: result, source: "glm_web_search" };
  } catch (error) {
    console.error("GLM geo targeting error:", error);

    try {
      const retryResponse = await glmClient.chat({
        model: "glm-5.1",
        messages: [
          {
            role: "system",
            content:
              "You are a geo targeting assistant for Malaysia. Use web search, then return ONLY raw JSON.",
          },
          {
            role: "user",
            content: `Search for geo targeting data for ${productName} in ${storeLocation}, Malaysia. Return JSON with targetZones, avoidZones, recommendedRadiusKm, targetDemographic, bestPlatform, bestTiming, adLanguage, overallConfidence, searchSummary, reasoning.`,
          },
        ],
        tools: [{ type: "web_search" }],
        tool_choice: "auto",
      });

      const retryContent = extractMessageContent(retryResponse);
      const retryResult = JSON.parse(stripJsonFences(retryContent));

      await setDoc(cacheRef, {
        result: retryResult,
        cachedAt: Date.now(),
        productName,
        storeLocation,
      });

      return { success: true, data: retryResult, source: "glm_retry" };
    } catch (retryError) {
      console.error("GLM retry also failed:", retryError);

      return {
        success: false,
        data: fallbackResult(productName, productCategory, storeLocation),
        source: "fallback_defaults",
      };
    }
  }
}
