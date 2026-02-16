import React from "react";
import { Routes, Route } from "react-router-dom";
import Upload from "@components/Upload";
import History from "@components/History";
import Result from "@components/Result";
import Navbar from "@components/common/Navbar";
import ErrorBoundary from "@components/common/ErrorBoundary";

const App = () => {
  return (
    <div className="min-h-screen bg-background text-slate-100">
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 py-8">
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<Upload />} />
            <Route path="/history" element={<History />} />
            <Route path="/result/:id" element={<Result />} />
          </Routes>
        </ErrorBoundary>
      </main>
    </div>
  );
};

export default App;

