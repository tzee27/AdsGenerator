import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AdCard from '../components/AdCard';
import '../styles/Main.css';

const ALL_PLATFORMS = ['All', 'TikTok', 'Shopee', 'Instagram', 'Facebook', 'Lazada'];
const ALL_FORMATS = ['All', 'Video', 'Image', 'Text'];

const SAMPLE_ADS = [
  {
    id: 1, platform: 'TikTok', format: 'Video', category: 'Fashion',
    caption: 'Trending now — our bamboo linen sets are flying off the shelves. Limited stock! Shop before Hari Raya rush hits. #HariRaya2025 #FashionTikTok',
    date: '12 Apr 2025',
    fullCaption: 'Trending now — our bamboo linen sets are flying off the shelves. Limited stock! Shop before Hari Raya rush hits. #HariRaya2025 #FashionTikTok #LimitedStock',
    hashtags: ['#HariRaya2025', '#FashionTikTok', '#LimitedStock', '#BambooLinen', '#TikTokFashion'],
    audience: 'Women 25–40, fashion-forward, urban lifestyle',
    bestTime: 'Thursday–Friday, 8–10 PM',
    pricing: 'Limited stock urgency — no discount needed',
  },
  {
    id: 2, platform: 'Shopee', format: 'Image', category: 'Electronics',
    caption: '11.11 MEGA SALE — Up to 60% off wireless earbuds. Bundle deal: Buy 2, get free shipping. Limited to first 200 orders.',
    date: '10 Apr 2025',
    fullCaption: '11.11 MEGA SALE — Up to 60% off wireless earbuds. Bundle deal: Buy 2, get free shipping. Limited to first 200 orders. Shopee Guaranteed — fast shipping within 1 day.',
    hashtags: ['#11.11Sale', '#ShopeeFinds', '#WirelessEarbuds', '#MegaSale', '#TechDeals'],
    audience: 'Tech-savvy buyers 18–35, students and remote workers',
    bestTime: 'Saturday morning, 9–11 AM',
    pricing: '60% off + free shipping on bundle',
  },
  {
    id: 3, platform: 'Instagram', format: 'Image', category: 'Skincare',
    caption: "Your skin deserves the best. Our vitamin C serum — now restocked. Perfect Valentine's gift for yourself. #SkincareCommunity",
    date: '8 Apr 2025',
    fullCaption: "Your skin deserves the best. Our vitamin C serum — now restocked after selling out in 3 days. Dermatologist-tested. Results in 14 days. Perfect Valentine's gift for yourself or someone special. #SkincareCommunity #GlassSkin",
    hashtags: ['#SkincareCommunity', '#GlassSkin', '#VitaminC', '#SkincareRoutine', '#Restock'],
    audience: 'Women 22–35, skincare enthusiasts',
    bestTime: 'Sunday evening, 7–9 PM',
    pricing: 'Full price — high demand justifies no discount',
  },
  {
    id: 4, platform: 'Facebook', format: 'Text', category: 'Home & Living',
    caption: 'Raya is coming! Refresh your home with our artisan cushion collection. Free delivery for orders above RM80. Shop now while stock lasts.',
    date: '5 Apr 2025',
    fullCaption: 'Raya is coming! Refresh your home with our artisan cushion collection — handcrafted, ethically made. Free delivery for orders above RM80. Bundle 3 and save 20%. Shop now while stock lasts.',
    hashtags: ['#RayaSale', '#HomeRefresh', '#ArtisanCrafts', '#FreeDelivery', '#HomeDecor'],
    audience: 'Married homeowners 28–50, family-oriented',
    bestTime: 'Weekday evenings, 7–9 PM',
    pricing: 'Free delivery above RM80 + 20% bundle discount',
  },
  {
    id: 5, platform: 'Lazada', format: 'Image', category: 'Sports',
    caption: 'New year, new goals. Our resistance band sets are a bestseller on Lazada. LazMall guaranteed. Bundle with yoga mat for extra savings.',
    date: '2 Apr 2025',
    fullCaption: 'New year, new goals. Our resistance band sets are the #1 bestseller in the Sports category on Lazada. LazMall guaranteed quality. Bundle with our yoga mat and save RM35. Ships same day.',
    hashtags: ['#FitnessGoals', '#LazadaMall', '#ResistanceBands', '#HomeGym', '#NewYearNewMe'],
    audience: 'Fitness enthusiasts 20–40, home workout crowd',
    bestTime: 'Monday morning, 7–9 AM',
    pricing: 'Bundle discount — save RM35 with yoga mat',
  },
  {
    id: 6, platform: 'TikTok', format: 'Video', category: 'Food & Beverage',
    caption: 'POV: you just found the best teh tarik mix at home. 3-in-1 pack, just add hot water. TikTok made me buy it. #FoodTok #MalaysiaMade',
    date: '28 Mar 2025',
    fullCaption: 'POV: you just found the best teh tarik mix at home. 3-in-1 pack, just add hot water. No barista needed. Authentic Malaysian taste — now ships nationwide. TikTok made me buy it. #FoodTok #MalaysiaMade',
    hashtags: ['#FoodTok', '#MalaysiaMade', '#TehTarik', '#HaltyDrinks', '#TikTokFood'],
    audience: 'Malaysian millennials 20–35, food lovers',
    bestTime: 'Weekend afternoons, 3–5 PM',
    pricing: 'Bundle 3-pack deal — save RM8',
  },
  {
    id: 7, platform: 'Shopee', format: 'Text', category: 'Baby & Kids',
    caption: 'Safe for babies, loved by parents. Our organic cotton onesies — BPA-free, GOTS certified. Free gift wrapping for baby shower orders.',
    date: '25 Mar 2025',
    fullCaption: 'Safe for babies, loved by parents. Our organic cotton onesies are BPA-free, GOTS certified, and tested by Malaysian pediatricians. Available in 6 sizes. Free gift wrapping for baby shower orders. Shopee Preferred Seller.',
    hashtags: ['#OrganicBaby', '#BabyEssentials', '#ShopeeKids', '#SafeForBaby', '#BabyShower'],
    audience: 'New parents 25–40, health-conscious buyers',
    bestTime: 'Saturday morning, 9–11 AM',
    pricing: 'Full price + free gift wrapping as value-add',
  },
  {
    id: 8, platform: 'Instagram', format: 'Video', category: 'Fitness',
    caption: 'Zero excuses. Our portable gym set fits in a backpack. Used by 10,000+ fitness lovers. Shop the link in bio.',
    date: '20 Mar 2025',
    fullCaption: 'Zero excuses. Our portable gym set fits in a backpack and gives you a full-body workout anywhere. Used by 10,000+ fitness lovers across Southeast Asia. Ships to Malaysia in 2 days. Shop the link in bio.',
    hashtags: ['#PortableGym', '#FitnessLifestyle', '#HomeWorkout', '#NoExcuses', '#FitnessTok'],
    audience: 'Fitness enthusiasts 18–35, travellers and remote workers',
    bestTime: 'Monday and Thursday, 6–8 AM',
    pricing: 'Early bird discount — 15% off first 100 orders',
  },
];

export default function Main() {
  const navigate = useNavigate();
  const [activePlatform, setActivePlatform] = useState('All');
  const [activeFormat, setActiveFormat] = useState('All');
  const [selectedAd, setSelectedAd] = useState(null);

  const filtered = SAMPLE_ADS.filter(ad => {
    const platformMatch = activePlatform === 'All' || ad.platform === activePlatform;
    const formatMatch = activeFormat === 'All' || ad.format === activeFormat;
    return platformMatch && formatMatch;
  });

  const platformClass = (p) => p.toLowerCase().replace(/[^a-z]/g, '');

  return (
    <div className="main-page">
      <div className="page-content">
        {/* Header */}
        <div className="page-header">
          <p className="page-header__label">Ad Samples</p>
          <h1 className="page-header__title">Content Library</h1>
          <p className="page-header__subtitle">Browse AI-generated ad examples across platforms and formats.</p>
        </div>

        {/* Filters — stacked two-row layout */}
        <div className="main-filters">
          <div className="main-filter-row">
            <span className="main-filter-label">Platform</span>
            <div className="main-filter-chips">
              {ALL_PLATFORMS.map(p => (
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
              {ALL_FORMATS.map(f => (
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

        {/* Grid */}
        <div className="main-ad-grid">
          {filtered.map(ad => (
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

      {/* ── Ad Detail Modal ── */}
      {selectedAd && (
        <div className="ad-modal-overlay" onClick={() => setSelectedAd(null)}>
          <div className="ad-modal" onClick={e => e.stopPropagation()}>
            {/* Modal header */}
            <div className="ad-modal__header">
              <div className="ad-modal__header-left">
                <span className={`ad-modal__platform-tag platform--${platformClass(selectedAd.platform)}`}>
                  {selectedAd.platform}
                </span>
                <div className="ad-modal__header-titles">
                  <h2>{selectedAd.category} Campaign</h2>
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

            {/* Preview & Main Content */}
            <div className="ad-modal__body">
              <div className="ad-modal__preview-premium">
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
              </div>

              {/* Caption Section */}
              <div className="ad-modal__section-premium">
                <div className="ad-modal__section-header">
                  <span className="ad-modal__section-line" />
                  <span className="ad-modal__section-title">AD CAPTION</span>
                </div>
                <div className="ad-modal__caption-box">
                  <p>{selectedAd.fullCaption}</p>
                </div>
              </div>

              {/* Hashtags */}
              <div className="ad-modal__section-premium">
                <div className="ad-modal__section-header">
                  <span className="ad-modal__section-line" />
                  <span className="ad-modal__section-title">HASHTAGS</span>
                </div>
                <div className="ad-modal__tags">
                  {selectedAd.hashtags.map(h => (
                    <span key={h} className="ad-modal__tag-pill">{h}</span>
                  ))}
                </div>
              </div>

              {/* Strategy Details Grid */}
              <div className="ad-modal__strategy-grid">
                {[
                  { icon: 'audience', label: 'Audience', val: selectedAd.audience },
                  { icon: 'clock', label: 'Timing', val: selectedAd.bestTime },
                  { icon: 'price', label: 'Pricing', val: selectedAd.pricing },
                ].map(item => (
                  <div key={item.label} className="ad-modal__strategy-item">
                    <span className="ad-modal__strategy-label">{item.label}</span>
                    <p className="ad-modal__strategy-val">{item.val}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="ad-modal__divider-line" />

            {/* Actions */}
            <div className="ad-modal__footer">
              <button
                className="ad-modal__btn-secondary"
                onClick={() => {
                  navigator.clipboard.writeText(selectedAd.fullCaption + '\n\n' + selectedAd.hashtags.join(' '));
                }}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
                Copy Content
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
