import '../styles/AdCard.css';

const platformColors = {
  TikTok: 'platform--tiktok',
  Shopee: 'platform--shopee',
  Instagram: 'platform--instagram',
  Facebook: 'platform--facebook',
  Lazada: 'platform--lazada',
};

export default function AdCard({ platform, format, category, caption, date, onClick }) {
  return (
    <div className="ad-card" onClick={onClick}>
      <div className="ad-card__header">
        <span className={`ad-card__platform ${platformColors[platform] || ''}`}>{platform}</span>
        <span className="ad-card__format">{format}</span>
      </div>
      <div className="ad-card__preview">
        <div className="ad-card__preview-shape" />
      </div>
      <div className="ad-card__caption">
        <p className="ad-card__category">{category}</p>
        <p className="ad-card__text">{caption}</p>
      </div>
      {date && <div className="ad-card__date">{date}</div>}
    </div>
  );
}
