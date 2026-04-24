/**
 * Auth barrel — all auth exports come from auth-context.tsx (JSX file).
 * Import from "@/lib/auth" as normal; this file re-exports everything.
 */
export {
  getSupabase,
  AuthProvider,
  useAuth,
  useRequireAuth,
} from "./auth-context";

