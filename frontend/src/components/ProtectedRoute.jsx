import { Navigate, useLocation } from 'react-router-dom';

import { useAuth } from '../auth/useAuth';

function ProtectedRoute({ children }) {
  const { autenticado } = useAuth();
  const location = useLocation();

  if (!autenticado) {
    return (
      <Navigate to="/login" replace state={{ from: location.pathname }} />
    );
  }

  return children;
}

export default ProtectedRoute;
