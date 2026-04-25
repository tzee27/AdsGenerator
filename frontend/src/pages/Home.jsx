import { useNavigate } from 'react-router-dom';
import '../styles/Home.css';

export default function Home() {
  const navigate = useNavigate();

  const trends = [
    { id: 1, title: 'UGC Style Videos', description: 'User-generated content continues to drive highest engagement on TikTok and Reels.', trend: '+24%', image: '/images/ugc_trend.png' },
    { id: 2, title: 'Carousel Posts', description: 'Multi-image posts on Instagram are seeing a resurgence in save rates.', trend: '+18%', image: '/images/carousel_trend.png' },
    { id: 3, title: 'Direct CTA', description: 'Clear, direct calls-to-action in the first 3 seconds improve conversion.', trend: '+12%', image: '/images/cta_trend.png' },
  ];

  const upcomingEvents = [
    { id: 1, name: 'Payday Sale', date: '25 April 2025', type: 'Shopping Event', priority: 'High' },
    { id: 2, name: 'Mother\'s Day', date: '11 May 2025', type: 'Holiday', priority: 'High' },
    { id: 3, name: 'Mid-Year Sale', date: '6 June 2025', type: 'Shopping Event', priority: 'Medium' },
    { id: 4, name: 'Black Friday', date: '28 November 2025', type: 'Shopping Event', priority: 'High' },
  ];

  return (
    <div className="page-content">
      <div className="page-header">
        <p className="page-header__label">Dashboard</p>
        <h1 className="page-header__title">Home</h1>
        <p className="page-header__subtitle">Discover current advertising trends and prepare for upcoming shopping holidays.</p>
      </div>

      <div className="home-grid">
        <section className="home-section">
          <div className="home-section__header">
            <h2>Current Trending Formats</h2>
            <p>Based on global e-commerce ad performance</p>
          </div>
          <div className="home-trends">
            {trends.map(t => (
              <div key={t.id} className="home-trend-card">
                <div className="home-trend-card__image-container">
                  <img src={t.image} alt={t.title} className="home-trend-card__image" />
                </div>
                <div className="home-trend-card__content">
                  <div className="home-trend-card__header">
                    <h3>{t.title}</h3>
                    <span className="home-trend-card__stat">{t.trend}</span>
                  </div>
                  <p>{t.description}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="home-section">
          <div className="home-section__header">
            <h2>Upcoming Special Dates</h2>
            <p>Plan your campaigns ahead of these key dates</p>
          </div>
          <div className="home-events">
            {upcomingEvents.map(e => (
              <div key={e.id} className="home-event-card">
                <div className="home-event-card__date">
                  <span className="home-event-card__month">{e.date.split(' ')[1]}</span>
                  <span className="home-event-card__day">{e.date.split(' ')[0]}</span>
                </div>
                <div className="home-event-card__info">
                  <h3>{e.name}</h3>
                  <span className="home-event-card__type">{e.type}</span>
                </div>
                <div className="home-event-card__action">
                  <button className="btn btn-primary btn-sm" onClick={() => navigate('/generate')}>Create Ad</button>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
