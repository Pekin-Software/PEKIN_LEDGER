import React, { useEffect, useState } from "react";
import { Routes, Route, useNavigate } from "react-router-dom";
import AdminDashboard from "./components/Admin Dashboard/admindashboard";
import ManagerDashboard from "./components/Manager Dashboard/managerdashboard";
import CashierDashboard from "./components/Cashier Dashboard/cashierdashboard";
import LandingPage from "./components/landingpage";
import "./App.css";
import Authentication from "./components/Authentications/authentication";
import Cookies from "js-cookie";
import { ApiProvider } from "./ApiContext.jsx";

function App() {
  const navigate = useNavigate();
  const [userRole, setUserRole] = useState(Cookies.get("role") || null);
  const [tenant, setTenant] = useState(Cookies.get("tenant") || null);
  
  useEffect(() => {
    const role = Cookies.get("role");
    const tenant = Cookies.get("tenant");
    setUserRole(role);
    setTenant(tenant);
  
    // If userRole exists, redirect to the appropriate dashboard
    if (role) {
      navigate(`/${role.toLowerCase()}`);
    }
  }, [navigate]);

  
  return (
   <ApiProvider>
     <div className="landing-container">
      <Routes>
        <Route path="/login" element={<Authentication defaultSignIn={true} navigate={useNavigate()} />} />
        <Route path="/signup" element={<Authentication defaultSignIn={false} />} />

        <Route path="/admin" element={userRole === "Admin" ? <AdminDashboard /> : <Authentication defaultSignIn={true} />} />
        <Route path="/manager" element={userRole === "Manager" ? <ManagerDashboard /> : <Authentication defaultSignIn={true} />} />
        <Route path="/cashier" element={userRole === "Cashier" ? <CashierDashboard /> : <Authentication defaultSignIn={true} />} />
        
        {/* Landing Page */}
        <Route path="/" element={<LandingPage />}/>
      </Routes>
    </div>
   </ApiProvider>
  );
}

export default App;
