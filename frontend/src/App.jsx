import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import UploadPage from "./pages/UploadPage";
import ExpenseDetail from "./pages/ExpenseDetail";

function Header() {
  return (
    <header className="sticky top-0 z-30 h-16 bg-white border-b border-gray-200 shadow-sm flex items-center px-4">
      <div className="max-w-4xl mx-auto w-full flex items-center justify-between">
        <Link to="/" className="text-lg font-bold text-indigo-600">
          🧾 Receipt Tracker
        </Link>
        <Link
          to="/upload"
          className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors text-sm"
        >
          + 영수증 추가
        </Link>
      </div>
    </header>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Header />
        <main className="max-w-4xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/expense/:id" element={<ExpenseDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
