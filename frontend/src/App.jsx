import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import Simulator from "./pages/Simulator.jsx";
import Detection from "./pages/Detection.jsx";
import History from "./pages/History.jsx";

const NAV_ITEMS = [
  { to: "/", label: "메인 대시보드", end: true },
  { to: "/simulator", label: "공정 시뮬레이터" },
  { to: "/detection", label: "이상 탐지 결과" },
  { to: "/history", label: "이력 관리" },
];

function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <aside className="sidebar">
          <h1>🏭 SemiSense</h1>
          <p className="subtitle">반도체 공정 이상 탐지</p>
          <nav>
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) => (isActive ? "active" : undefined)}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </aside>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/simulator" element={<Simulator />} />
            <Route path="/detection" element={<Detection />} />
            <Route path="/history" element={<History />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
