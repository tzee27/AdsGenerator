import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Login from './pages/Login';
import SignUp from './pages/SignUp';
import Main from './pages/Main';
import ContentGeneration from './pages/ContentGeneration';
import Database from './pages/Database';
import Profile from './pages/Profile';
import './index.css';

const AUTH_ROUTES = ['/login', '/signup'];

export default function App() {
  const location = useLocation();
  const isAuthPage = AUTH_ROUTES.includes(location.pathname);

  return (
    <div className="app-shell">
      {!isAuthPage && <Sidebar />}

      <main className={isAuthPage ? 'app-main-full' : 'app-main'}>
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<SignUp />} />
          <Route path="/main" element={<Main />} />
          <Route path="/generate" element={<ContentGeneration />} />
          <Route path="/database" element={<Database />} />
          <Route path="/profile" element={<Profile />} />
        </Routes>
      </main>
    </div>
  );
}
