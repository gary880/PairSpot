"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function NavBar() {
  const pathname = usePathname();

  const links = [
    { href: "/posts", label: "Feed" },
    { href: "/posts/create", label: "發文" },
    { href: "/couple", label: "情侶" },
    { href: "/account", label: "帳號" },
    { href: "/login", label: "登入" },
    { href: "/register", label: "註冊" },
  ];

  return (
    <nav className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-md items-center justify-between px-4 py-3">
        <span className="text-base font-bold text-rose-600">PairSpot</span>
        <div className="flex gap-4">
          {links.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`text-sm font-medium ${
                pathname === href
                  ? "text-rose-600"
                  : "text-gray-500 hover:text-gray-800"
              }`}
            >
              {label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
