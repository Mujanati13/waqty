import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import frFR from 'antd/locale/fr_FR';
import Login from './pages/Login';
import ESNDashboard from './pages/ESNDashboard';
import ConsultantCRA from './pages/ConsultantCRA';
import ProtectedRoute from './components/ProtectedRoute';
import { isLoggedIn, getUserRole } from './helper/auth';
import './App.css';

// Home redirect based on auth state
const HomeRedirect = () => {
  if (!isLoggedIn()) {
    return <Navigate to="/login" replace />;
  }
  
  const role = getUserRole();
  if (role === 'esn') {
    return <Navigate to="/esn/dashboard" replace />;
  } else if (role === 'consultant') {
    return <Navigate to="/consultant/cra" replace />;
  }
  
  return <Navigate to="/login" replace />;
};

function App() {
  return (
    <ConfigProvider locale={frFR}>
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          
          {/* ESN Routes */}
          <Route 
            path="/esn/dashboard" 
            element={
              <ProtectedRoute allowedRoles={['esn']}>
                <ESNDashboard />
              </ProtectedRoute>
            } 
          />
          
          {/* Consultant Routes */}
          <Route 
            path="/consultant/cra" 
            element={
              <ProtectedRoute allowedRoles={['consultant']}>
                <ConsultantCRA />
              </ProtectedRoute>
            } 
          />
          
          {/* Default Route */}
          <Route path="/" element={<HomeRedirect />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
