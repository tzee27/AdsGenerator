import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import "../styles/Auth.css";

const adTypes = [
  { id: "video", label: "Video Ad", desc: "TikTok, Reels, Stories" },
  { id: "image", label: "Image Ad", desc: "Banners, Carousels" },
  { id: "text", label: "Text Ad", desc: "Listing Boost, Search" },
];

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setError("");
      setLoading(true);
      await login(form.email, form.password);
      navigate("/home");
    } catch (err) {
      setError("Failed to log in: " + err.message);
    }
    setLoading(false);
  };

  return (
    <div className="auth-page">
      <div className="auth-container">
        {/* Left panel */}
        <div className="auth-panel auth-panel--brand">
          <div className="auth-brand">
            <div className="auth-brand__logo">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
              >
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <h1 className="auth-brand__name">AdPilot</h1>
            <p className="auth-brand__tagline">
              AI-powered advertising decisions, built for e-commerce sellers.
            </p>
          </div>

          <div className="auth-features">
            {[
              {
                label: "Inventory Analysis",
                desc: "Upload your CSV and let GLM read your stock data.",
              },
              {
                label: "Smart Recommendations",
                desc: "Seasonal, trend-aware ad strategy for every product.",
              },
              {
                label: "Ready-to-Use Content",
                desc: "Ad copy, captions, hashtags — generated instantly.",
              },
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
        <div className="auth-panel auth-panel--form">
          <div className="auth-form-header">
            <p className="auth-form-header__label">Welcome back</p>
            <h2>Sign in to AdPilot</h2>
            {error && (
              <div
                className="auth-error"
                style={{ color: "red", marginTop: "10px" }}
              >
                {error}
              </div>
            )}
          </div>

          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label" htmlFor="login-email">
                Email address
              </label>
              <input
                id="login-email"
                type="email"
                className="form-input"
                placeholder="you@example.com"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="login-password">
                Password
              </label>
              <input
                id="login-password"
                type="password"
                className="form-input"
                placeholder="Enter your password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                required
              />
            </div>

            <button
              disabled={loading}
              type="submit"
              className="btn btn-primary btn-lg auth-submit-btn"
            >
              {loading ? "Signing In..." : "Sign In"}
              {!loading && (
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  width="16"
                  height="16"
                >
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              )}
            </button>
          </form>

          <div className="auth-divider">
            <span>New to AdPilot?</span>
          </div>

          <Link
            to="/signup"
            className="btn btn-secondary btn-lg auth-signup-link"
          >
            Create an account
          </Link>
        </div>
      </div>
    </div>
  );
}
