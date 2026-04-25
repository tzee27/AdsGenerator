import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import '../styles/Auth.css';

const adTypes = [
  { id: 'video', label: 'Video Ad', desc: 'TikTok, Reels, Stories' },
  { id: 'image', label: 'Image Ad', desc: 'Banners, Carousels, Product Photos' },
  { id: 'text', label: 'Text Ad', desc: 'Listing Boost, Search Ads' },
];

const platforms = ['Shopee', 'Lazada', 'TikTok Shop', 'Instagram', 'Facebook'];

export default function SignUp() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    businessName: '',
    preferredAdType: '',
    platforms: [],
  });

  const { signup } = useAuth();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const togglePlatform = (p) => {
    setForm(f => ({
      ...f,
      platforms: f.platforms.includes(p)
        ? f.platforms.filter(x => x !== p)
        : [...f.platforms, p],
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setError('');
      setLoading(true);
      await signup(form.email, form.password, form);
      navigate('/home');
    } catch (err) {
      setError('Failed to create an account: ' + err.message);
    }
    setLoading(false);
  };

  return (
    <div className="auth-page">
      <div className="auth-container auth-container--signup">
        {/* Left panel */}
        <div className="auth-panel auth-panel--brand">
          <div className="auth-brand">
            <div className="auth-brand__logo">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <h1 className="auth-brand__name">AdSmart</h1>
            <p className="auth-brand__tagline">Join thousands of sellers making smarter ad decisions.</p>
          </div>

          <div className="auth-features">
            {[
              { label: 'No Marketing Team Needed', desc: 'GLM does the strategy work for you.' },
              { label: 'Multi-Platform Ready', desc: 'Shopee, Lazada, TikTok, Instagram, Facebook.' },
              { label: 'Trend-Aware Content', desc: 'Always relevant, always timely.' },
            ].map((f) => (
              <div key={f.label} className="auth-feature">
                <div className="auth-feature__dot" />
                <div>
                  <strong>{f.label}</strong>
                  <p>{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right panel - Form */}
        <div className="auth-panel auth-panel--form auth-panel--form-tall">
          <div className="auth-form-header">
            <p className="auth-form-header__label">Get started</p>
            <h2>Create your account</h2>
            {error && <div className="auth-error" style={{ color: 'red', marginTop: '10px' }}>{error}</div>}
          </div>

          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="auth-form__row">
              <div className="form-group">
                <label className="form-label" htmlFor="signup-name">Full Name</label>
                <input
                  id="signup-name"
                  type="text"
                  className="form-input"
                  placeholder="Your name"
                  value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="signup-business">Business / Store Name</label>
                <input
                  id="signup-business"
                  type="text"
                  className="form-input"
                  placeholder="Your store"
                  value={form.businessName}
                  onChange={e => setForm({ ...form, businessName: e.target.value })}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="signup-email">Email address</label>
              <input
                id="signup-email"
                type="email"
                className="form-input"
                placeholder="you@example.com"
                value={form.email}
                onChange={e => setForm({ ...form, email: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="signup-password">Password</label>
              <input
                id="signup-password"
                type="password"
                className="form-input"
                placeholder="At least 8 characters"
                value={form.password}
                onChange={e => setForm({ ...form, password: e.target.value })}
                required
              />
            </div>

            {/* Ad Type Selection */}
            <div className="form-group">
              <label className="form-label">Preferred Ad Type</label>
              <div className="auth-adtype-grid">
                {adTypes.map(t => (
                  <button
                    key={t.id}
                    type="button"
                    className={`auth-adtype-card ${form.preferredAdType === t.id ? 'auth-adtype-card--active' : ''}`}
                    onClick={() => setForm({ ...form, preferredAdType: t.id })}
                  >
                    <span className="auth-adtype-card__label">{t.label}</span>
                    <span className="auth-adtype-card__desc">{t.desc}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Platforms */}
            <div className="form-group">
              <label className="form-label">Platforms you sell on</label>
              <div className="auth-platforms">
                {platforms.map(p => (
                  <button
                    key={p}
                    type="button"
                    className={`chip ${form.platforms.includes(p) ? 'chip--active' : ''}`}
                    onClick={() => togglePlatform(p)}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>

            <button disabled={loading} type="submit" className="btn btn-primary btn-lg auth-submit-btn">
              {loading ? 'Creating Account...' : 'Create Account'}
              {!loading && (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              )}
            </button>
          </form>

          <div className="auth-divider">
            <span>Already have an account? <Link to="/login" className="auth-link">Sign in</Link></span>
          </div>
        </div>
      </div>
    </div>
  );
}
