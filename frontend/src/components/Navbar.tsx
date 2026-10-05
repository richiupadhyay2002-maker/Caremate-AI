"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { usePathname } from "next/navigation";

export default function Navbar() {
  const { user, token, logout } = useAuth();
  const pathname = usePathname();

  const navLinks = [
    { href: "/", label: "Home" },
        ...(token && user?.role === "patient"
      ? [{ href: "/dashboard", label: "My Care" }]
      : []),
    ...(token && user?.role === "doctor"
      ? [{ href: "/doctors/me", label: "My Patients" }]
      : []),
    ...(token && (user?.role as string) === "admin"
      ? [{ href: "/doctors/me", label: "Admin Panel" }]
      : []),
    ...(token ? [{ href: "/ask", label: "Ask AI" }] : []),
  ];

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <Link href="/">
                <span className="text-xl font-bold text-primary cursor-pointer">
                  Caremate AI
                </span>
              </Link>
            </div>
            <div className="hidden sm:-mb-px sm:flex sm:space-x-8">
              {navLinks.map((link) => (
                <Link key={link.href} href={link.href}>
                  <span
                    className={
                      pathname === link.href
                        ? "border-primary text-gray-900"
                        : "border-transparent text-gray-500 hover:text-gray-700"
                    }
                  >
                    <span className="inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium cursor-pointer">
                      {link.label}
                    </span>
                  </span>
                </Link>
              ))}
            </div>
          </div>
          <div className="hidden sm:ml-6 sm:flex sm:items-center">
            {token && user ? (
              <>
                <span className="text-sm text-gray-500 mr-4">
                  Logged in as <strong>{user.email}</strong> ({user.role})
                </span>
                <button
                  onClick={logout}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  Logout
                </button>
              </>
            ) : (
              <Link href="/login">
                <span className="text-sm text-gray-500 hover:text-gray-700 cursor-pointer">
                  Login
                </span>
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}