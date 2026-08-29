import { Navigate, Route, Routes } from 'react-router-dom';
import { SessionProvider, useSession } from './context/SessionContext';
import TopNav from './components/TopNav';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ProjectsPage from './pages/ProjectsPage';
import ProjectDetailPage from './pages/ProjectDetailPage';
import MapPage from './pages/MapPage';
import './styles/tokens.css';
import './styles/global.css';

function RequireSession({ children }) {
  const { session } = useSession();
  if (!session) return <Navigate to="/" replace />;
  return children;
}

function AppRoutes() {
  return (
    <div className="app-shell">
      <TopNav />
      <Routes>
        <Route path="/" element={<LoginPage />} />
        <Route
          path="/dashboard"
          element={
            <RequireSession>
              <DashboardPage />
            </RequireSession>
          }
        />
        <Route
          path="/projects"
          element={
            <RequireSession>
              <ProjectsPage />
            </RequireSession>
          }
        />
        <Route
          path="/projects/:projectId"
          element={
            <RequireSession>
              <ProjectDetailPage />
            </RequireSession>
          }
        />
        <Route
          path="/map"
          element={
            <RequireSession>
              <MapPage />
            </RequireSession>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

function App() {
  return (
    <SessionProvider>
      <AppRoutes />
    </SessionProvider>
  );
}

export default App;
