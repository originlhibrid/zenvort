import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { Toast } from './components/Toast';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { Landing } from './pages/Landing';
import { Login } from './pages/Login';
import { Signup } from './pages/Signup';
import { Dashboard } from './pages/Dashboard';
import { ApiKey } from './pages/ApiKey';
import { Billing } from './pages/Billing';
import { Admin } from './pages/Admin';
import { Store } from './store';

function ProtectedLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  if (!Store.isAuthenticated()) return <Navigate to="/login" />;
  return (
    <div className="flex min-h-screen">
      <div className={`fixed inset-0 z-40 bg-black/50 md:hidden ${mobileOpen ? '' : 'hidden'}`} onClick={() => setMobileOpen(false)} />
      <div className={`fixed inset-y-0 left-0 z-50 transform ${mobileOpen ? 'translate-x-0' : '-translate-x-full'} transition-transform md:hidden`}>
        <Sidebar onClose={() => setMobileOpen(false)} />
      </div>
      <div className="hidden md:block w-64 flex-shrink-0"><Sidebar /></div>
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar onMenuOpen={() => setMobileOpen(true)} />
        <main className="flex-1 bg-slate-50 overflow-auto"><Outlet /></main>
      </div>
    </div>
  );
}

function AdminRoute() {
  const user = Store.getUser();
  if (!user || user.role !== 'admin') return <Navigate to="/dashboard" />;
  return <Outlet />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Toast />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route element={<ProtectedLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/keys" element={<ApiKey />} />
          <Route path="/billing" element={<Billing />} />
          <Route element={<AdminRoute />}>
            <Route path="/admin" element={<Admin />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  );
}