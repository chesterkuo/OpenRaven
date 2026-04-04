import { Routes, Route, NavLink, useLocation } from "react-router-dom";
import AskPage from "./pages/AskPage";
import StatusPage from "./pages/StatusPage";
import IngestPage from "./pages/IngestPage";
import GraphPage from "./pages/GraphPage";
import WikiPage from "./pages/WikiPage";
import ConnectorsPage from "./pages/ConnectorsPage";

export default function App() {
  const location = useLocation();
  const isGraphPage = location.pathname === "/graph";

  return (
    <div className="h-screen flex flex-col bg-gray-950 text-gray-100">
      <nav className="border-b border-gray-800 px-6 py-3 flex items-center gap-6 shrink-0">
        <span className="text-lg font-bold text-white tracking-tight">OpenRaven</span>
        <NavLink to="/" className={({ isActive }) => isActive ? "text-blue-400" : "text-gray-400 hover:text-gray-200"}>Ask</NavLink>
        <NavLink to="/ingest" className={({ isActive }) => isActive ? "text-blue-400" : "text-gray-400 hover:text-gray-200"}>Add Files</NavLink>
        <NavLink to="/graph" className={({ isActive }) => isActive ? "text-blue-400" : "text-gray-400 hover:text-gray-200"}>Graph</NavLink>
        <NavLink to="/wiki" className={({ isActive }) => isActive ? "text-blue-400" : "text-gray-400 hover:text-gray-200"}>Wiki</NavLink>
        <NavLink to="/connectors" className={({ isActive }) => isActive ? "text-blue-400" : "text-gray-400 hover:text-gray-200"}>Connectors</NavLink>
        <NavLink to="/status" className={({ isActive }) => isActive ? "text-blue-400" : "text-gray-400 hover:text-gray-200"}>Status</NavLink>
      </nav>
      <main className={isGraphPage ? "flex-1 flex flex-col min-h-0" : "max-w-4xl mx-auto px-6 py-8 w-full flex-1"}>
        <Routes>
          <Route path="/" element={<AskPage />} />
          <Route path="/ingest" element={<IngestPage />} />
          <Route path="/graph" element={<GraphPage />} />
          <Route path="/wiki" element={<WikiPage />} />
          <Route path="/connectors" element={<ConnectorsPage />} />
          <Route path="/status" element={<StatusPage />} />
        </Routes>
      </main>
    </div>
  );
}
