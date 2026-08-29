import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useSession } from '../context/SessionContext';

const EMBLEM = 'https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg';

export default function TopNav() {
  const { session, logout } = useSession();
  const location = useLocation();
  const navigate = useNavigate();

  if (!session) return null;

  const links =
    session.role === 'officer'
      ? [
          { to: '/dashboard', label: 'Dashboard' },
          { to: '/projects', label: 'Projects' },
          { to: '/map', label: 'Map' },
        ]
      : [
          { to: '/dashboard', label: 'Overview' },
          { to: '/projects', label: 'Projects' },
          { to: '/map', label: 'Map' },
        ];

  return (
    <div className="topbar-row card" style={{ borderRadius: 0, marginBottom: 20, boxShadow: 'none', borderTop: 'none', borderLeft: 'none', borderRight: 'none' }}>
      <div className="brand">
        <img src={EMBLEM} alt="Emblem of India" />
        <h1>
          MPLADS <span>MONITOR</span>
        </h1>
      </div>
      <nav>
        {links.map((l) => (
          <Link key={l.to} to={l.to} className={`nav-link ${location.pathname.startsWith(l.to) ? 'active' : ''}`}>
            {l.label}
          </Link>
        ))}
      </nav>
      <div className="user-chip">
        <img src={`https://i.pravatar.cc/100?u=${session.username}`} alt="" />
        <span>
          {session.role === 'officer' ? 'Officer' : 'Citizen'} <b>{session.username}</b>
        </span>
        <a
          className="logout-link"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            logout();
            navigate('/');
          }}
        >
          Logout
        </a>
      </div>
    </div>
  );
}
