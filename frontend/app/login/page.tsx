"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { signInWithEmail, signUpWithEmail, signInWithGoogle } = useAuth();
  const router = useRouter();

  const [mode, setMode] = useState<"sign_in" | "sign_up">("sign_in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    if (mode === "sign_in") {
      const { error: err } = await signInWithEmail(email, password);
      if (err) { setError(err); setLoading(false); }
      else router.push("/");
    } else {
      const { error: err } = await signUpWithEmail(email, password);
      if (err) { setError(err); setLoading(false); }
      else { setSuccess("Check your email to confirm your account, then sign in."); setLoading(false); }
    }
  };

  const handleGoogle = async () => {
    setLoading(true);
    await signInWithGoogle();
  };

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-65px)]">
      <div className="w-full max-w-sm space-y-6">

        <div className="text-center">
          <h1 className="text-2xl font-bold text-white tracking-tight">
            {mode === "sign_in" ? "Welcome back" : "Create account"}
          </h1>
          <p className="text-sm text-[#A3A3A3] mt-1">
            {mode === "sign_in"
              ? "Sign in to T1T2.ai to continue"
              : "Start evaluating your IELTS writing"}
          </p>
        </div>

        <div className="card-container p-6 space-y-5">
          <button
            onClick={handleGoogle}
            disabled={loading}
            className="w-full btn-outline justify-center bg-[#422006] text-[#EAB308] border-[#EAB308]/50 hover:bg-[#EAB308]/20"
          >
            Continue with Google
          </button>

          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-white/10" />
            <span className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest">or</span>
            <div className="flex-1 h-px bg-white/10" />
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label htmlFor="email" className="section-label">Email</label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-base w-full bg-[#2A2A2A] border border-[#FFFFFF]/10 p-3 rounded-md text-sm"
                placeholder="you@example.com"
                disabled={loading}
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="password" className="section-label">Password</label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-base w-full bg-[#2A2A2A] border border-[#FFFFFF]/10 p-3 rounded-md text-sm"
                placeholder="••••••••"
                disabled={loading}
              />
            </div>

            {error && <div className="text-xs text-red-400 font-medium">{error}</div>}
            {success && <div className="text-xs text-[#16A34A] font-medium">{success}</div>}

            <button
              type="submit"
              disabled={loading}
              className="w-full btn-outline justify-center bg-[#422006] text-[#EAB308] border-[#EAB308]/50 hover:bg-[#EAB308]/20 mt-2"
            >
              {loading ? "..." : (mode === "sign_in" ? "Sign in" : "Create account")}
            </button>
          </form>

          <p className="text-center text-xs text-[#A3A3A3]">
            {mode === "sign_in" ? "Don't have an account? " : "Already have an account? "}
            <button
              type="button"
              onClick={() => { setMode(mode === "sign_in" ? "sign_up" : "sign_in"); setError(null); setSuccess(null); }}
              className="text-white hover:underline transition-all"
            >
              {mode === "sign_in" ? "Sign up" : "Sign in"}
            </button>
          </p>
        </div>

      </div>
    </div>
  );
}
