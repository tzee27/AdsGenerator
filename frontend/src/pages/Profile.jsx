import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { doc, updateDoc, collection, addDoc } from 'firebase/firestore';
import { db } from '../lib/firebase';
import '../styles/Profile.css';

const PLATFORMS = ['Shopee', 'Lazada', 'TikTok Shop', 'Instagram', 'Facebook'];
const AD_TYPES = [
  { id: 'video', label: 'Video Ad' },
  { id: 'image', label: 'Image Ad' },
  { id: 'text', label: 'Text Ad' },
];

export default function Profile() {
  const navigate = useNavigate();
  const { currentUser, userData, logout } = useAuth();
  const [editing, setEditing] = useState(false);
  
  const [profile, setProfile] = useState({
    name: '',
    email: '',
    businessName: '',
    preferredAdType: 'video',
    platforms: [],
  });
  const [draft, setDraft] = useState(profile);

  useEffect(() => {
    if (currentUser || userData) {
      const loadedProfile = {
        name: userData?.name || 'New User',
        email: currentUser?.email || '',
        businessName: userData?.businessName || '',
        preferredAdType: userData?.preferredAdType || 'video',
        platforms: userData?.platforms || [],
      };
      setProfile(loadedProfile);
      setDraft(loadedProfile);
    }
  }, [currentUser, userData]);

  const togglePlatform = (p) => {
    setDraft(d => ({
      ...d,
      platforms: d.platforms.includes(p)
        ? d.platforms.filter(x => x !== p)
        : [...d.platforms, p],
    }));
  };

  const saveChanges = async () => {
    if (currentUser) {
      try {
        const userRef = doc(db, 'users', currentUser.uid);
        await updateDoc(userRef, {
          name: draft.name,
          businessName: draft.businessName,
          preferredAdType: draft.preferredAdType,
          platforms: draft.platforms
        });
        setProfile(draft);
        setEditing(false);
      } catch (error) {
        console.error("Error updating profile:", error);
        alert("Failed to save profile changes.");
      }
    }
  };

  const cancelEdit = () => {
    setDraft(profile);
    setEditing(false);
  };

  const loadDemoData = async () => {
    if (!currentUser) return;
    try {
      const demoAds = [
        {
          createdAt: new Date().toISOString(),
          platform: 'TikTok',
          format: 'Video',
          category: 'Fashion',
          productName: 'Bamboo Linen Set (Queen)',
          caption: 'Trending now — our bamboo linen sets are flying off the shelves. Limited stock! Shop before Hari Raya rush hits. #HariRaya2025 #FashionTikTok',
          fullCaption: 'Trending now — our bamboo linen sets are flying off the shelves. Limited stock! Shop before Hari Raya rush hits. #HariRaya2025 #FashionTikTok #LimitedStock',
          headline: 'Hari Raya Promo: Limited Stock!',
          callToAction: 'Shop Now',
          hashtags: ['#HariRaya2025', '#FashionTikTok', '#LimitedStock', '#BambooLinen', '#TikTokFashion'],
          audience: 'Women 25–40, fashion-forward, urban lifestyle',
          bestTime: 'Thursday–Friday, 8–10 PM',
          pricing: 'Limited stock urgency — no discount needed',
          budget: 'RM 100',
          angle: 'Urgency & Scarcity',
          image: '/images/sample_bamboo_linen.png',
          status: 'completed',
          source: 'ads/finalize',
          isLive: true,
          isDeleted: false
        },
        {
          createdAt: new Date(Date.now() - 86400000 * 1).toISOString(),
          platform: 'Shopee',
          format: 'Image',
          category: 'Electronics',
          productName: 'Wireless Earbuds Pro',
          caption: '11.11 MEGA SALE — Up to 60% off wireless earbuds. Bundle deal: Buy 2, get free shipping. Limited to first 200 orders.',
          fullCaption: '11.11 MEGA SALE — Up to 60% off wireless earbuds. Bundle deal: Buy 2, get free shipping. Limited to first 200 orders. Shopee Guaranteed — fast shipping within 1 day.',
          headline: 'Up to 60% OFF + Free Shipping',
          callToAction: 'Add to Cart',
          hashtags: ['#11.11Sale', '#ShopeeFinds', '#WirelessEarbuds', '#MegaSale', '#TechDeals'],
          audience: 'Tech-savvy buyers 18–35, students and remote workers',
          bestTime: 'Saturday morning, 9–11 AM',
          pricing: '60% off + free shipping on bundle',
          budget: 'RM 250',
          angle: 'Huge Discount & Value',
          image: '/images/sample_earbuds.png',
          status: 'completed',
          source: 'ads/finalize',
          isLive: true,
          isDeleted: false
        },
        {
          createdAt: new Date(Date.now() - 86400000 * 2).toISOString(),
          platform: 'Instagram',
          format: 'Image',
          category: 'Skincare',
          productName: 'Vitamin C Glow Serum',
          caption: "Your skin deserves the best. Our vitamin C serum — now restocked. Perfect Valentine's gift for yourself. #SkincareCommunity",
          fullCaption: "Your skin deserves the best. Our vitamin C serum — now restocked after selling out in 3 days. Dermatologist-tested. Results in 14 days. Perfect Valentine's gift for yourself or someone special. #SkincareCommunity #GlassSkin",
          headline: 'Back in Stock: The Glow Secret',
          callToAction: 'Shop Now',
          hashtags: ['#SkincareCommunity', '#GlassSkin', '#VitaminC', '#SkincareRoutine', '#Restock'],
          audience: 'Women 22–35, skincare enthusiasts',
          bestTime: 'Sunday evening, 7–9 PM',
          pricing: 'Full price — high demand justifies no discount',
          budget: 'RM 150',
          angle: 'Premium & Exclusive',
          image: '/images/sample_serum.png',
          status: 'completed',
          source: 'ads/finalize',
          isDeleted: false
        },
        {
          createdAt: new Date(Date.now() - 86400000 * 3).toISOString(),
          platform: 'Facebook',
          format: 'Text',
          category: 'Home & Living',
          productName: 'Artisan Cushion Collection',
          caption: 'Raya is coming! Refresh your home with our artisan cushion collection. Free delivery for orders above RM80. Shop now while stock lasts.',
          fullCaption: 'Raya is coming! Refresh your home with our artisan cushion collection — handcrafted, ethically made. Free delivery for orders above RM80. Bundle 3 and save 20%. Shop now while stock lasts.',
          headline: 'Refresh Your Home for Raya',
          callToAction: 'Shop the Collection',
          hashtags: ['#RayaSale', '#HomeRefresh', '#ArtisanCrafts', '#FreeDelivery', '#HomeDecor'],
          audience: 'Married homeowners 28–50, family-oriented',
          bestTime: 'Weekday evenings, 7–9 PM',
          pricing: 'Free delivery above RM80 + 20% bundle discount',
          budget: 'RM 80',
          angle: 'Bundle Savings',
          image: '/images/sample_cushion.png',
          status: 'completed',
          source: 'ads/finalize',
          isDeleted: false
        }
      ];

      for (const ad of demoAds) {
        await addDoc(collection(db, 'users', currentUser.uid, 'savedAds'), ad);
      }
      alert("4 Rich Demo Ads successfully loaded to Database! Check your History tab.");
    } catch (error) {
      console.error("Failed to load demo data", error);
      alert("Error loading demo data.");
    }
  };

  const stats = [
    { label: 'Campaigns Generated', value: '24', icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
      </svg>
    )},
    { label: 'Platforms Used', value: profile.platforms.length, icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
        <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
        <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
      </svg>
    )},
    { label: 'This Month', value: '6', icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
        <line x1="16" y1="2" x2="16" y2="6" />
        <line x1="8" y1="2" x2="8" y2="6" />
        <line x1="3" y1="10" x2="21" y2="10" />
      </svg>
    )},
    { label: 'Avg. Quality Score', value: '9.1', icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
      </svg>
    )},
  ];

  return (
    <div className="page-content">
      <div className="page-header">
        <p className="page-header__label">Account</p>
        <h1 className="page-header__title">Your Profile</h1>
      </div>

      <div className="profile-layout">
        {/* Avatar + stats */}
        <div className="profile-sidebar-panel">
          <div className="profile-avatar-card">
            <div className="profile-avatar">
              <span className="profile-avatar__initials">
                {profile.name ? profile.name.split(' ').map(n => n?.[0]).join('').toUpperCase().slice(0, 2) : 'U'}
              </span>
            </div>
            <h2 className="profile-avatar__name">{profile.name}</h2>
            <p className="profile-avatar__business">{profile.businessName}</p>
            <p className="profile-avatar__email">{profile.email}</p>

            {!editing && (
              <button className="btn btn-secondary btn-sm profile-edit-btn" onClick={() => { setDraft(profile); setEditing(true); }}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                </svg>
                Edit Profile
              </button>
            )}
          </div>

          {/* Stats Grid */}
          <div className="profile-stats-grid">
            {stats.map(s => (
              <div key={s.label} className="profile-stat-card">
                <div className="profile-stat-card__icon">{s.icon}</div>
                <div className="profile-stat-card__info">
                  <span className="profile-stat-card__value">{s.value}</span>
                  <span className="profile-stat-card__label">{s.label}</span>
                </div>
              </div>
            ))}
          </div>

          <button
            className="btn btn-ghost profile-history-btn"
            onClick={() => navigate('/main')}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" width="16" height="16">
              <ellipse cx="12" cy="5" rx="9" ry="3" />
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
            </svg>
            View Generation History
          </button>
        </div>

        {/* Edit Form */}
        <div className="profile-main-panel">
          {editing ? (
            <div className="profile-form-card">
              <h3 className="profile-form-card__title">Edit Profile</h3>

              <div className="profile-form-grid">
                <div className="form-group">
                  <label className="form-label" htmlFor="profile-name">Full Name</label>
                  <input
                    id="profile-name"
                    type="text"
                    className="form-input"
                    value={draft.name}
                    onChange={e => setDraft({ ...draft, name: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="profile-business">Business / Store Name</label>
                  <input
                    id="profile-business"
                    type="text"
                    className="form-input"
                    value={draft.businessName}
                    onChange={e => setDraft({ ...draft, businessName: e.target.value })}
                  />
                </div>

                <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                  <label className="form-label" htmlFor="profile-email">Email Address</label>
                  <input
                    id="profile-email"
                    type="email"
                    className="form-input"
                    value={draft.email}
                    onChange={e => setDraft({ ...draft, email: e.target.value })}
                  />
                </div>
              </div>

              <div className="divider" />

              <div className="form-group">
                <label className="form-label">Preferred Ad Type</label>
                <div className="profile-adtype-row">
                  {AD_TYPES.map(t => (
                    <button
                      key={t.id}
                      type="button"
                      className={`profile-adtype-btn ${draft.preferredAdType === t.id ? 'profile-adtype-btn--active' : ''}`}
                      onClick={() => setDraft({ ...draft, preferredAdType: t.id })}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Platforms</label>
                <div className="profile-platforms">
                  {PLATFORMS.map(p => (
                    <button
                      key={p}
                      type="button"
                      className={`chip ${draft.platforms.includes(p) ? 'chip--active' : ''}`}
                      onClick={() => togglePlatform(p)}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>

              <div className="profile-form-actions">
                <button className="btn btn-ghost" onClick={cancelEdit}>Cancel</button>
                <button className="btn btn-primary" onClick={saveChanges}>Save Changes</button>
              </div>
            </div>
          ) : (
            <div className="profile-info-card">
              <h3 className="profile-info-card__title">Account Details</h3>

              <div className="profile-info-grid">
                {[
                  { label: 'Full Name', value: profile.name },
                  { label: 'Business', value: profile.businessName },
                  { label: 'Email', value: profile.email },
                  { label: 'Preferred Ad Type', value: AD_TYPES.find(t => t.id === profile.preferredAdType)?.label || '—' },
                ].map(d => (
                  <div key={d.label} className="profile-info-item">
                    <span className="profile-info-item__label">{d.label}</span>
                    <span className="profile-info-item__value">{d.value}</span>
                  </div>
                ))}
              </div>

              <div className="divider" />

              <div className="profile-info-section">
                <span className="form-label" style={{ display: 'block', marginBottom: 10 }}>Selling Platforms</span>
                <div className="profile-platforms">
                  {profile.platforms.map(p => (
                    <span key={p} className="chip chip--active">{p}</span>
                  ))}
                  {profile.platforms.length === 0 && <span className="profile-no-platforms">None selected</span>}
                </div>
              </div>

              <div className="divider" />

              <div className="profile-danger-zone">
                <h4>Account Actions</h4>
                <div className="profile-danger-actions">
                  <button className="btn btn-ghost btn-sm" onClick={async () => { await logout(); navigate('/login'); }}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" width="14" height="14">
                      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                      <polyline points="16 17 21 12 16 7" />
                      <line x1="21" y1="12" x2="9" y2="12" />
                    </svg>
                    Sign Out
                  </button>
                  <button className="btn btn-primary btn-sm" onClick={loadDemoData} style={{marginLeft: '10px'}}>
                    Load Demo Data
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
