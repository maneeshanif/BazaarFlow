"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";

function getInitialTheme(): "light" | "dark" {
  if (typeof window === "undefined") {
    return "light";
  }
  const savedTheme = window.localStorage.getItem("theme") as "light" | "dark" | null;
  if (savedTheme) {
    return savedTheme;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark">(() => getInitialTheme());

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem("theme", theme);
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [theme]);

  const toggleTheme = () => {
    const newTheme = theme === "light" ? "dark" : "light";
    setTheme(newTheme);
    localStorage.setItem("theme", newTheme);
    
    if (newTheme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  };

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggleTheme}
      className="w-10 h-10 rounded-full hover:bg-white/10 transition-colors"
      aria-label="Toggle theme"
    >
      {theme === "light" ? (
        <Moon className="w-5 h-5 text-[rgb(var(--muted))] hover:text-white transition-colors" />
      ) : (
        <Sun className="w-5 h-5 text-yellow-400 hover:text-yellow-300 transition-colors" />
      )}
    </Button>
  );
}

