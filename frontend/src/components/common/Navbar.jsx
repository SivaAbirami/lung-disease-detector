import React from "react";
import { Link, NavLink } from "react-router-dom";
import { FiActivity } from "react-icons/fi";

const navLinkClass = ({ isActive }) =>
  [
    "px-3 py-2 rounded-md text-sm font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500",
    isActive ? "bg-slate-800 text-primary-50" : "text-slate-300 hover:bg-slate-800"
  ].join(" ");

import { useAuth } from "../../context/AuthContext";
import { FiLogOut } from "react-icons/fi";

const Navbar = () => {
  const { user, logout } = useAuth();

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
          <NavLink to="/dashboard" className={navLinkClass}>
            Dashboard
          </NavLink>

          <div className="h-6 w-px bg-slate-700 mx-2" />

          {user ? (
            <div className="flex items-center gap-4">
              <span className="text-sm text-slate-400">Hello, {user.username}</span>
              <button
                onClick={logout}
                className="text-slate-400 hover:text-white p-2 rounded-full hover:bg-slate-800 transition-colors"
                title="Logout"
              >
                <FiLogOut />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                to="/login"
                className="text-slate-300 hover:text-white text-sm font-medium px-3 py-2"
              >
                Sign In
              </Link>
              <Link
                to="/register"
                className="bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors shadow-sm"
              >
                Get Started
              </Link>
            </div>
          )}
        </div>

      </nav>
    </header>
  );
};

export default Navbar;

