import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useNavigate,
} from 'react-router-dom';

import './App.css';

import AdminDashboard from './AdminDashboard';
import { AuthProvider } from './auth/AuthProvider';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import Biblioteca from './pages/Biblioteca';
import Cadastro from './pages/Cadastro';
import Home from './pages/Home';
import Login from './pages/Login';

function AdminPage() {
  const navigate = useNavigate();

  return <AdminDashboard onVoltar={() => navigate('/')} />;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/admin" element={<AdminPage />} />

          <Route element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="login" element={<Login />} />
            <Route path="cadastro" element={<Cadastro />} />
            <Route
              path="biblioteca"
              element={
                <ProtectedRoute>
                  <Biblioteca />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
