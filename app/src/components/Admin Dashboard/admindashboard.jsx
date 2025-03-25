import { useState, useEffect } from "react";
import { Bell, Search, Settings, LogOut, LayoutDashboard, Package, BarChart, Truck, ShoppingCart, Store } from "lucide-react";
import "./admindashboard.css";
import Stores from "./Store Dashboard/store";
import InventoryDashboard from "../Inventory/inventoryDashboard";
import Cookies from "js-cookie";
import { useNavigate } from "react-router-dom";
const logo = "/logo.jpg";

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [activePage, setActivePage] = useState("dashboard");

  const user = Cookies.get("user");

  useEffect(() => {
    setTimeout(() => setLoading(false), 2000); // Simulate loading time
  }, []);
  const handleLogout = () => {
    // Remove authentication tokens and user details from cookies
    Cookies.remove("access_token");
    Cookies.remove("refresh_token");
    Cookies.remove("role");
    Cookies.remove("tenant");
    Cookies.remove("user");
    
    // Redirect user to the login page
    navigate('/');
  };
  
  const renderContent = () => {
    switch (activePage) {
      case "inventory":
        return <InventoryDashboard />;
      case "store":
        return <Stores />;
      default:
        return (
          <div className="dashboard-items">
            <div className="dashboard-column left-column">
              <div className="dashboard-card"> {user}</div>
              <div className="dashboard-card">Dashboard Item 2</div>
            </div>
            <div className="dashboard-column right-column">
              <div className="dashboard-card">Dashboard Item 3</div>
              <div className="dashboard-card">Dashboard Item 4</div>
              <div className="dashboard-card">Dashboard Item 5</div>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="dashboard-container">
      {/* Sidebar */}
      <aside className="sidebar">
       <img src={logo} alt="logo" />
        <nav className="nav-links">
          <a 
            href="#" 
            className={activePage === "dashboard" ? "active" : ""} 
            onClick={() => setActivePage("dashboard")}
          >
            <LayoutDashboard /> Dashboard
          </a>
          <a 
            href="#" 
            className={activePage === "inventory" ? "active" : ""} 
            onClick={() => setActivePage("inventory")}
          >
            <Package /> Inventory
          </a>
          <a href="#"><BarChart /> Reports</a>
          <a href="#"><Truck /> Suppliers</a>
          <a href="#"><ShoppingCart /> Orders</a>
          <a 
            href="#"
            className={activePage === "store" ? "active" : ""} 
            onClick={() => setActivePage("store")}
          ><Store /> Manage Store</a>
        </nav>
        <div className="bottom-links">
          <a href="#" className="settings">
            <Settings /> Settings
          </a>
          <a href="#" className="logout" onClick={handleLogout}>
            <LogOut /> Logout
          </a>
        </div>
      </aside>

      {/* Main Content */}
      <div className="main-content">
        {/* Top Navbar */}
        <header className="top-navbar">
          <div className="search-bar">
            <Search className="search-icon" />
            <input type="text" placeholder="Search..." className="search-input" />
          </div>
          <div className="profile-section">
            <Bell className="icon" />
            <img src="https://via.placeholder.com/40" alt="Profile" className="profile-pic" />
          </div>
        </header>

        {/* Dashboard Content */}
        <main className="content-area">
          {loading ? (
            <div className="loading-placeholder">
              <div className="skeleton"></div>
              <div className="skeleton"></div>
              <div className="skeleton"></div>
            </div>
          ) : (
            renderContent()
          )}
        </main>
      </div>
    </div>
  );
}




