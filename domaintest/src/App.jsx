// import { useState } from 'react'
// import reactLogo from './assets/react.svg'
// import viteLogo from '/vite.svg'
// import './App.css'

// function App() {
//   const [count, setCount] = useState(0)

//   return (
//     <>
//       <div>
//         <a href="https://vite.dev" target="_blank">
//           <img src={viteLogo} className="logo" alt="Vite logo" />
//         </a>
//         <a href="https://react.dev" target="_blank">
//           <img src={reactLogo} className="logo react" alt="React logo" />
//         </a>
//       </div>
//       <h1>Vite + React</h1>
//       <div className="card">
//         <button onClick={() => setCount((count) => count + 1)}>
//           count is {count}
//         </button>
//         <p>
//           Edit <code>src/App.jsx</code> and save to test HMR
//         </p>
//       </div>
//       <p className="read-the-docs">
//         Click on the Vite and React logos to learn more
//       </p>
//     </>
//   )
// }

// export default App


import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

const getSubdomain = () => {
  const host = window.location.hostname;
  const parts = host.split(".");

  // Handle localhost subdomains
  if (host.includes("localhost")) {
    return parts.length > 1 ? parts[0] : "main";
  }

  return parts.length > 2 ? parts[0] : "main";
};

const MainPage = () => <h1>Main Website</h1>;
const SubPage1 = () => <h1>Subdomain 1 Page</h1>;
const SubPage2 = () => <h1>Subdomain 2 Page</h1>;
const NotFound = () => <h1>404 - Not Found</h1>;

const App = () => {
  const subdomain = getSubdomain();

  return (
    <Router>
      <Routes>
        {subdomain === "main" && <Route path="/" element={<MainPage />} />}
        {subdomain === "sub1" && <Route path="/" element={<SubPage1 />} />}
        {subdomain === "sub2" && <Route path="/" element={<SubPage2 />} />}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Router>
  );
};

export default App;
