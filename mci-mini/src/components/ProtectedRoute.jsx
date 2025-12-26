import { Navigate, useLocation } from 'react-router-dom';
import { isLoggedIn, getUserRole } from '../helper/auth';

// Protected route wrapper
const ProtectedRoute = ({ children, allowedRoles = [] }) => {
  const location = useLocation();
  
  if (!isLoggedIn()) {
    // Redirect to login if not authenticated
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  const userRole = getUserRole();
  
  // If roles are specified, check if user has permission
  if (allowedRoles.length > 0 && !allowedRoles.includes(userRole)) {
    // Redirect to appropriate dashboard based on role
    if (userRole === 'esn') {
      return <Navigate to="/esn/dashboard" replace />;
    } else if (userRole === 'consultant') {
      return <Navigate to="/consultant/cra" replace />;
    }
    return <Navigate to="/login" replace />;
  }

  return children;
};

export default ProtectedRoute;
