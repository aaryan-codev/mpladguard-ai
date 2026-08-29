import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSession } from '../context/SessionContext';

const EMBLEM = 'https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg';

export default function LoginPage() {
  const [role, setRole] = useState('officer');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const { login } = useSession();
  const navigate = useNavigate();

  function handleSubmit(e) {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError('Enter a username and password to continue.');
      return;
    }
    // NOTE: this is a demo role-selector for the hackathon MVP, not real
    // authentication -- there is no backend auth/session check here.
    login(username.trim(), role);
    navigate('/dashboard');
  }

  return (
    <div className="app-shell" style={{ alignItems: 'center' }}>
      <div className="topbar">
        <img className="emblem" src={EMBLEM} alt="Emblem of India" />
        <h1>
          MPLADS <span>MONITOR</span>
        </h1>
        <p>
          AI-Powered Monitoring &amp; Anomaly Detection Platform
          <br />
          for MPLADS Scheme Implementation
        </p>
      </div>

      <div className="card card-lifted" style={{ width: '100%', maxWidth: 460, padding: 28 }}>
        <h2 style={{ textAlign: 'center', color: 'var(--navy)', fontSize: 22 }}>Welcome back</h2>
        <p style={{ textAlign: 'center', color: 'var(--text-faint)', fontSize: 12.5, margin: '6px 0 20px' }}>
          Sign in to continue to your account
        </p>

        <p style={{ textAlign: 'center', fontWeight: 600, margin: '10px 0', color: 'var(--navy)', fontSize: 13 }}>
          Login as
        </p>
        <div style={{ display: 'flex', gap: 10, marginBottom: 18 }}>
          <RoleCard
            active={role === 'officer'}
            onClick={() => setRole('officer')}
            emoji="👨‍💼"
            title="Government Officer"
            desc="Manage projects and monitor AI risk analysis"
            color="var(--green)"
          />
          <RoleCard
            active={role === 'citizen'}
            onClick={() => setRole('citizen')}
            emoji="👥"
            title="Citizen"
            desc="View public project transparency data"
            color="var(--blue)"
          />
        </div>

        <form onSubmit={handleSubmit}>
          {error && <div className="error-banner">⚠️ {error}</div>}
          <label className="field-label">👤 Username</label>
          <input
            className="field-input"
            type="text"
            placeholder="Enter any username (demo)"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <label className="field-label">🔒 Password</label>
          <div style={{ position: 'relative' }}>
            <input
              className="field-input"
              type={showPassword ? 'text' : 'password'}
              placeholder="Enter any password (demo)"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <span
              style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', cursor: 'pointer' }}
              onClick={() => setShowPassword((s) => !s)}
            >
              👁️
            </span>
          </div>
          <button className="btn" type="submit" style={{ width: '100%', marginTop: 16 }}>
            🔒 Login
          </button>
        </form>
        <p style={{ textAlign: 'center', fontSize: 11, color: 'var(--text-faint)', marginTop: 14 }}>
          Demo login for the SIH prototype -- any username/password is accepted.
        </p>
      </div>

      <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', justifyContent: 'center', maxWidth: 900, margin: '28px 0', padding: '0 16px' }}>
        <Feature icon="🛡️" title="AI-Powered" desc="Isolation Forest anomaly detection on road projects" />
        <Feature icon="📊" title="Transparent" desc="Real project data, explainable risk factors" />
        <Feature icon="🔒" title="Responsible" desc="Flags anomalies for human review, never confirms fraud" />
      </div>

      <div className="footer-bar">
        <div>Ministry of Statistics &amp; Programme Implementation -- Government of India (SIH 2026 prototype)</div>
        <div>MPLADGuard-AI</div>
      </div>
    </div>
  );
}

function RoleCard({ active, onClick, emoji, title, desc, color }) {
  return (
    <div
      onClick={onClick}
      style={{
        flex: 1,
        border: `1.5px solid ${active ? color : 'var(--border)'}`,
        background: active ? 'var(--bg-muted)' : 'white',
        borderRadius: 12,
        padding: 14,
        textAlign: 'center',
        cursor: 'pointer',
        position: 'relative',
      }}
    >
      {active && (
        <div
          style={{
            position: 'absolute',
            top: 6,
            right: 6,
            width: 18,
            height: 18,
            borderRadius: '50%',
            background: color,
            color: 'white',
            fontSize: 10,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          ✓
        </div>
      )}
      <div style={{ fontSize: 24 }}>{emoji}</div>
      <h4 style={{ fontSize: 12.5, color, marginTop: 6 }}>{title}</h4>
      <p style={{ fontSize: 9.5, color: 'var(--text-faint)', marginTop: 3, lineHeight: 1.3 }}>{desc}</p>
    </div>
  );
}

function Feature({ icon, title, desc }) {
  return (
    <div style={{ display: 'flex', gap: 8, flex: 1, minWidth: 200 }}>
      <span>{icon}</span>
      <div>
        <b style={{ fontSize: 11, color: 'var(--navy)' }}>{title}</b>
        <p style={{ fontSize: 10, color: 'var(--text-muted)' }}>{desc}</p>
      </div>
    </div>
  );
}
