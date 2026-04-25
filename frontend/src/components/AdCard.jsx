import '../styles/AdCard.css';

const platformColors = {
  TikTok: 'platform--tiktok',
  Shopee: 'platform--shopee',
  Instagram: 'platform--instagram',
  Facebook: 'platform--facebook',
  Lazada: 'platform--lazada',
};

export default function AdCard({
  platform,
  format,
  category,
  caption,
  date,
  onClick,
  image,
  isLive,
}) {
  return (
    <div className="ad-card" onClick={onClick}>
      <div className="ad-card__header">
        <span className={`ad-card__platform ${platformColors[platform] || ''}`}>{platform}</span>
        <div className="ad-card__header-right">
          {isLive && <span className="ad-card__live-pill">LIVE</span>}
          <span className="ad-card__format">{format}</span>
        </div>
      </div>
      <div className="ad-card__preview">
        {image ? (
          <img src={image} alt={category || 'Generated ad preview'} className="ad-card__preview-image" />
        ) : (
          <div className="ad-card__preview-shape" />
        )}
      </div>
      <div className="ad-card__caption">
        <p className="ad-card__category">{category}</p>
        <p className="ad-card__text">{caption}</p>
      </div>
      {date && <div className="ad-card__date">{date}</div>}
    </div>
  );
}
