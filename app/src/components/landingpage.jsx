// import React, { useState } from "react";
// import Authentication from "./Authentications/authentication";
// import "./landingpage.css";
// import { useNavigate } from 'react-router-dom';
// const LandingPage = () => {
//   const [showAuth, setShowAuth] = useState(false);
//   const [defaultSignIn, setDefaultSignIn] = useState(true);
//   const navigate = useNavigate();
//   const openAuth = (isSignIn) => {
//     setDefaultSignIn(isSignIn);
//     setShowAuth(true);
//   };

//   return (
//     <div className="landing-container">
//       {showAuth ? (
//         <Authentication defaultSignIn={defaultSignIn} setShowAuth={setShowAuth} />
//       ) : (
//         <>
//           {/* Header */}
//           <header className="landing-header">
//             <div className="landing-logo">Pekin Ledger</div>
//             <nav className="landing-nav">
//               <button className="login-btn" aria-label="Login" onClick={() => openAuth(true)}>Login</button>
//               <button className="signup-btn" aria-label="Sign Up" onClick={() => openAuth(false)}>Sign Up</button>
//             </nav>
//           </header>

//           {/* Main Content */}
//           <main className="landing-content">
//             <h2>Welcome to Pekin Ledger</h2>
//             <p>Your go-to platform for the latest financial insights and news.</p>
//             <button className="landing-button" onClick={() => openAuth(false)}>Get Started</button>
//           </main>

//           {/* Footer */}
//           <footer className="landing-footer">
//             &copy; {new Date().getFullYear()} Pekin Ledger. All rights reserved.
//           </footer>
//         </>
//       )}
//     </div>
//   );
// };

// export default LandingPage;


import React, { useState } from "react";
import { useNavigate } from "react-router-dom"; // Import the useNavigate hook
import Authentication from "./Authentications/authentication";
import "./landingpage.css";

const LandingPage = () => {
  const [showAuth, setShowAuth] = useState(false);
  const [defaultSignIn, setDefaultSignIn] = useState(true);

  // Initialize the navigate function
  const navigate = useNavigate();

  const openAuth = (isSignIn) => {
    setDefaultSignIn(isSignIn);
    setShowAuth(true);
  };

  const handleGetStarted = () => {
    // Navigate to the signup page when Get Started is clicked
    navigate("/signup");
  };

  return (
    <div className="landing-container">
      {showAuth ? (
        <Authentication defaultSignIn={defaultSignIn} setShowAuth={setShowAuth} />
      ) : (
        <>
          {/* Header */}
          <header className="landing-header">
            <div className="landing-logo">Pekin Ledger</div>
            <nav className="landing-nav">
            <button className="login-btn" aria-label="Login" onClick={() => navigate("/login")}>
                Login
            </button>

            <button className="signup-btn" aria-label="Sign Up" onClick={() => navigate("/signup")}>
                Sign Up
            </button>

            </nav>
          </header>

          {/* Main Content */}
          <main className="landing-content">
            <h2>Welcome to Pekin Ledger</h2>
            <p>Your go-to platform for the latest financial insights and news.</p>
            <button className="landing-button" onClick={handleGetStarted}>Get Started</button>
          </main>

          {/* Footer */}
          <footer className="landing-footer">
            &copy; {new Date().getFullYear()} Pekin Ledger. All rights reserved.
          </footer>
        </>
      )}
    </div>
  );
};

export default LandingPage;
