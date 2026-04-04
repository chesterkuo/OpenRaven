import { Routes, Route, NavLink } from "react-router-dom";
import AskPage from "./pages/AskPage";
import StatusPage from "./pages/StatusPage";
import IngestPage from "./pages/IngestPage";

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <nav className="border-b border-gray-800 px-6 py-3 flex items-center gap-6">
        <span className="text-lg font-bold text-white tracking-tight">OpenRaven</span>
        <NavLink to="/" className={({ isActive }) => isActive ? "text-blue-400" : "text-gray-400 hover:text-gray-200"}>Ask</NavLink>
        <NavLink to="/ingest" className={({ isActive }) => isActive ? "text-blue-400" : "text-gray-400 hover:text-gray-200"}>Add Files</NavLink>
        <NavLink to="/status" className={({ isActive }) => isActive ? "text-blue-400" : "text-gray-400 hover:text-gray-200"}>Status</NavLink>
      </nav>
      <main className="max-w-4xl mx-auto px-6 py-8">
        <Routes>
          <Route path="/" element={<AskPage />} />
          <Route path="/ingest" element={<IngestPage />} />
          <Route path="/status" element={<StatusPage />} />
        </Routes>
      </main>
    </div>
  );
}
