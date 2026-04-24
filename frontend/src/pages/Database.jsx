import { useState, Fragment } from 'react';
import '../styles/Database.css';

const HISTORY = [
  {
    id: 'GEN-001', date: '12 Apr 2025', product: 'Vitamin C Serum 30ml',
    platform: 'TikTok', format: 'Video', status: 'Completed',
    caption: 'Only 12 left and they\'re going FAST. Meet your new glow secret: our Vitamin C Serum. #GlassSkin #RayaGlow',
    hashtags: '#VitaminC #GlassSkin #SkincareRoutine #RayaGlow',
  },
  {
    id: 'GEN-002', date: '10 Apr 2025', product: 'Bamboo Linen Set (Queen)',
    platform: 'Shopee', format: 'Image', status: 'Completed',
    caption: 'Raya Home Refresh Promo — 15% off + free pillowcase gift. Limited stock while supplies last.',
    hashtags: '#HomeRefresh #RayaSale #ShopeeFinds',
  },
  {
    id: 'GEN-003', date: '8 Apr 2025', product: 'Wireless Earbuds Pro',
    platform: 'Instagram', format: 'Image', status: 'Completed',
    caption: 'Flash deal — RM99 for 48 hours only. Only 8 units left. Shop now via link in bio.',
    hashtags: '#TechDeals #WirelessEarbuds #FlashSale',
  },
  {
    id: 'GEN-004', date: '5 Apr 2025', product: 'Resistance Band Set',
    platform: 'Facebook', format: 'Text', status: 'Completed',
    caption: 'New year, new goals. Our resistance band sets are a bestseller. Bundle with yoga mat for extra savings.',
    hashtags: '#FitnessGoals #ResistanceBands #HomeWorkout',
  },
  {
    id: 'GEN-005', date: '2 Apr 2025', product: 'Organic Cotton Onesie',
    platform: 'Shopee', format: 'Image', status: 'Completed',
    caption: 'Safe for babies, loved by parents. BPA-free and GOTS certified. Free gift wrapping for baby shower orders.',
    hashtags: '#BabyEssentials #OrganicBaby #ShopeeKids',
  },
];

export default function Database() {
  const [expanded, setExpanded] = useState(null);
  const [search, setSearch] = useState('');
  const [filterPlatform, setFilterPlatform] = useState('All');

  const platforms = ['All', ...new Set(HISTORY.map(h => h.platform))];

  const filtered = HISTORY.filter(h => {
    const matchSearch = h.product.toLowerCase().includes(search.toLowerCase()) ||
      h.id.toLowerCase().includes(search.toLowerCase());
    const matchPlatform = filterPlatform === 'All' || h.platform === filterPlatform;
    return matchSearch && matchPlatform;
  });

  return (
    <div className="page-content">
      <div className="page-header">
        <p className="page-header__label">Records</p>
        <h1 className="page-header__title">Generation History</h1>
        <p className="page-header__subtitle">All your past AI-generated ad campaigns in one place.</p>
      </div>

      {/* Controls */}
      <div className="db-controls">
        <div className="db-search">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="db-search__icon">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            className="form-input db-search__input"
            placeholder="Search by product or ID..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            id="db-search"
          />
        </div>

        <div className="db-filter-chips">
          {platforms.map(p => (
            <button
              key={p}
              className={`chip ${filterPlatform === p ? 'chip--active' : ''}`}
              onClick={() => setFilterPlatform(p)}
            >
              {p}
            </button>
          ))}
        </div>

        <span className="db-count">{filtered.length} record{filtered.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Table */}
      <div className="db-table-wrap">
        <table className="db-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Date</th>
              <th>Product</th>
              <th>Platform</th>
              <th>Format</th>
              <th>Status</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(h => (
              <Fragment key={h.id}>
                <tr className={expanded === h.id ? 'db-row--expanded' : ''}>
                  <td><span className="db-id">{h.id}</span></td>
                  <td className="db-date">{h.date}</td>
                  <td className="db-product">{h.product}</td>
                  <td><span className="db-platform-badge">{h.platform}</span></td>
                  <td className="db-format">{h.format}</td>
                  <td><span className={`badge badge--${h.status === 'Completed' ? 'success' : 'pending'}`}>{h.status}</span></td>
                  <td>
                    <button
                      className="db-expand-btn"
                      onClick={() => setExpanded(expanded === h.id ? null : h.id)}
                      aria-label={expanded === h.id ? 'Collapse' : 'Expand'}
                    >
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        width="16"
                        height="16"
                        style={{ transform: expanded === h.id ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s ease' }}
                      >
                        <polyline points="6 9 12 15 18 9" />
                      </svg>
                    </button>
                  </td>
                </tr>

                {expanded === h.id && (
                  <tr key={`${h.id}-detail`} className="db-detail-row">
                    <td colSpan={7}>
                      <div className="db-detail">
                        <div className="db-detail__section">
                          <span className="db-detail__label">Generated Caption</span>
                          <p>{h.caption}</p>
                        </div>
                        <div className="db-detail__section">
                          <span className="db-detail__label">Hashtags</span>
                          <p className="db-detail__hashtags">{h.hashtags}</p>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>

        {filtered.length === 0 && (
          <div className="db-empty">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" width="40" height="40">
              <ellipse cx="12" cy="5" rx="9" ry="3" />
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
            </svg>
            <p>No records found.</p>
          </div>
        )}
      </div>
    </div>
  );
}
