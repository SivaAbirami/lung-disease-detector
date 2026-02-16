import React from "react";
import { Link, NavLink } from "react-router-dom";
import { FiActivity } from "react-icons/fi";

const navLinkClass = ({ isActive }) =>
  [
    "px-3 py-2 rounded-md text-sm font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500",
    isActive ? "bg-slate-800 text-primary-50" : "text-slate-300 hover:bg-slate-800"
  ].join(" ");

const Navbar = () => {
  return (
    <header className="bg-surface border-b border-slate-800">
      <nav
        className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between"
        aria-label="Main navigation"
      >
        <Link to="/" className="flex items-center gap-2">
          <div className="h-9 w-9 rounded-full bg-primary-500 flex items-center justify-center shadow-lg">
            <FiActivity className="text-white" aria-hidden="true" />
          </div>
          <div className="flex flex-col">
            <span className="font-semibold text-slate-50">
              Lung Disease Detector
            </span>
            <span className="text-xs text-slate-400">
              AI-assisted chest X-ray triage
            </span>
          </div>
        </Link>
        <div className="flex items-center gap-2">
          <NavLink to="/" className={navLinkClass}>
            Upload
          </NavLink>
          <NavLink to="/history" className={navLinkClass}>
            History
          </NavLink>
        </div>
      </nav>
    </header>
  );
};

export default Navbar;

