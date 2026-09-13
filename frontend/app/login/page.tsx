"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiPost, setToken, ApiError } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("demo@therang.com");
  const [password, setPassword] = useState("demo1234");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const path = mode === "login" ? "/api/auth/login" : "/api/auth/register";
      const body: any = { email, password };
      if (mode === "register") body.property_name = "My Villa";
      const res = await apiPost<{ access_token: string }>(path, body);
      setToken(res.access_token);
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-10">
          <div className="text-xs tracking-[0.2em] text-bronze uppercase mb-2">The Rang</div>
          <h1 className="font-serif text-3xl">Intelligence</h1>
          <p className="text-sm text-muted mt-2">Revenue, Guest & Experience Intelligence</p>
        </div>

        <form onSubmit={submit} className="bg-warmwhite border border-taupedark/60 rounded-lg p-8 shadow-card space-y-4">
          <div>
            <label className="block text-xs uppercase tracking-wide text-muted mb-1">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-taupedark rounded-md px-3 py-2 bg-white focus:outline-none focus:ring-1 focus:ring-bronze"
            />
          </div>
          <div>
            <label className="block text-xs uppercase tracking-wide text-muted mb-1">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-taupedark rounded-md px-3 py-2 bg-white focus:outline-none focus:ring-1 focus:ring-bronze"
            />
          </div>
          {error && <p className="text-sm text-terracotta">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-charcoal text-warmwhite rounded-md py-2.5 text-sm tracking-wide hover:bg-bronzedark transition disabled:opacity-60"
          >
            {loading ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
          <button
            type="button"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
            className="w-full text-xs text-muted underline underline-offset-2"
          >
            {mode === "login" ? "New property? Create an account" : "Already have an account? Sign in"}
          </button>
        </form>

        <p className="text-center text-xs text-muted mt-6">
          Demo login is pre-filled — <span className="text-charcoal">demo@therang.com / demo1234</span>
        </p>
      </div>
    </div>
  );
}
