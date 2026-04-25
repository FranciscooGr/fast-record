/**
 * Navbar — Shared navigation bar for all dashboard views.
 *
 * Features:
 * - Logo + "Fast Record" title (links to /d/:publicId)
 * - Hamburger menu with navigation links
 * - Accepts optional extra menu items via props (e.g. "Resetear Cuenta")
 * - Auto-closes on navigation or outside click
 * - Reads publicId from URL via useParams
 *
 * Following rerender-no-inline-components: no components defined inside this one.
 */

import { useState, useCallback } from 'react';
import { Link, useParams, useLocation } from 'react-router-dom';
import {
  ShoppingBag,
  Menu,
  X,
  LayoutDashboard,
  FileBarChart,
  LogOut,
} from 'lucide-react';

/* ═══════════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════════ */
export interface NavbarExtraMenuItem {
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
  /** Additional classes for the button (e.g. "text-red-500") */
  className?: string;
  /** Additional classes for the icon wrapper */
  iconClassName?: string;
}

interface NavbarProps {
  /** Extra menu items appended after the navigation links (page-specific actions). */
  extraMenuItems?: NavbarExtraMenuItem[];
}

/* ═══════════════════════════════════════════════════════════════
   Navigation links — defined outside the component (rendering-hoist-jsx)
   ═══════════════════════════════════════════════════════════════ */
const NAV_LINKS = [
  {
    to: (id: string) => `/d/${id}`,
    label: 'Panel Principal',
    icon: <LayoutDashboard size={16} strokeWidth={2.5} />,
    matchEnd: true, // only exact match
  },
  {
    to: (id: string) => `/d/${id}/reports`,
    label: 'Informes',
    icon: <FileBarChart size={16} strokeWidth={2.5} />,
    matchEnd: false,
  },
] as const;

/* ═══════════════════════════════════════════════════════════════
   Component
   ═══════════════════════════════════════════════════════════════ */
export default function Navbar({ extraMenuItems = [] }: NavbarProps) {
  const { publicId } = useParams<{ publicId: string }>();
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);

  const closeMenu = useCallback(() => setIsOpen(false), []);
  const toggleMenu = useCallback(() => setIsOpen((prev) => !prev), []);

  const safePublicId = publicId ?? '';

  return (
    <nav className="bg-white/95 backdrop-blur-md px-5 py-4 shadow-[0_4px_24px_rgba(0,0,0,0.03)] sticky top-0 z-30 border-b border-surface-muted/50">
      <div className="flex justify-between items-center relative w-full">

        {/* ── Left: Logo + Title ──────────────────────────── */}
        <Link
          to={`/d/${safePublicId}`}
          className="flex items-center gap-3 group"
          onClick={closeMenu}
        >
          <div className="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center text-white font-bold text-sm shadow-md group-hover:bg-brand-700 transition-colors">
            <ShoppingBag size={20} strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="font-bold text-ink leading-tight text-lg">Fast Record</h1>
            <p className="text-[10px] uppercase font-bold tracking-widest text-ink-muted">Management</p>
          </div>
        </Link>

        {/* ── Right: Hamburger Button ────────────────────── */}
        <button
          id="navbar-menu-toggle"
          onClick={toggleMenu}
          className="w-10 h-10 flex items-center justify-center rounded-xl bg-surface-muted text-ink-muted hover:text-ink hover:bg-brand-50 transition-colors active:scale-95"
          aria-label={isOpen ? 'Cerrar menú' : 'Abrir menú'}
          aria-expanded={isOpen}
        >
          {isOpen
            ? <X size={22} strokeWidth={2.5} />
            : <Menu size={22} strokeWidth={2.5} />
          }
        </button>

        {/* ── Dropdown Menu ──────────────────────────────── */}
        {isOpen && (
          <>
            {/* Backdrop — closes menu on outside click */}
            <div
              className="fixed inset-0 z-40"
              onClick={closeMenu}
              aria-hidden="true"
            />

            <div className="absolute right-0 top-12 mt-2 w-60 bg-white rounded-2xl shadow-card border border-brand-50/50 p-2 z-50">

              {/* Navigation Links */}
              {NAV_LINKS.map((link) => {
                const href = link.to(safePublicId);
                const isActive = link.matchEnd
                  ? location.pathname === href
                  : location.pathname.startsWith(href);

                return (
                  <Link
                    key={href}
                    to={href}
                    onClick={closeMenu}
                    className={`w-full flex items-center gap-3 px-3 py-3 text-sm font-semibold rounded-xl transition-colors ${
                      isActive
                        ? 'text-brand-600 bg-brand-50'
                        : 'text-ink-muted hover:text-ink hover:bg-surface-muted'
                    }`}
                  >
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                      isActive ? 'bg-brand-100 text-brand-600' : 'bg-surface'
                    }`}>
                      {link.icon}
                    </div>
                    {link.label}
                  </Link>
                );
              })}

              {/* Divider — only if there are extra items */}
              {extraMenuItems.length > 0 && (
                <div className="h-px bg-surface-muted/60 my-1 mx-2" />
              )}

              {/* Extra Menu Items (page-specific actions) */}
              {extraMenuItems.map((item) => (
                <button
                  key={item.label}
                  onClick={() => {
                    item.onClick();
                    closeMenu();
                  }}
                  className={`w-full flex items-center gap-3 px-3 py-3 text-sm font-semibold rounded-xl transition-colors ${
                    item.className ?? 'text-ink-muted hover:text-ink hover:bg-surface-muted'
                  }`}
                >
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    item.iconClassName ?? 'bg-surface'
                  }`}>
                    {item.icon}
                  </div>
                  {item.label}
                </button>
              ))}

              {/* Divider before logout */}
              <div className="h-px bg-surface-muted/60 my-1 mx-2" />

              {/* Logout */}
              <button
                onClick={() => {
                  if (window.confirm('¿Estás seguro de que deseas cerrar sesión?')) {
                    closeMenu();
                    // TODO: implement actual logout logic
                    console.log('Cerrando sesión...');
                  }
                }}
                className="w-full flex items-center gap-3 px-3 py-3 text-sm font-semibold text-ink-muted hover:text-ink hover:bg-surface-muted rounded-xl transition-colors"
              >
                <div className="w-8 h-8 rounded-lg bg-surface flex items-center justify-center">
                  <LogOut size={16} strokeWidth={2.5} />
                </div>
                Cerrar Sesión
              </button>
            </div>
          </>
        )}
      </div>
    </nav>
  );
}
