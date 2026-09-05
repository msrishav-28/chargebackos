import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { loginRequest, setToken } from "@/lib/ops-api";
import { OpsApiError } from "@/lib/ops-api";

export const Route = createFileRoute("/login")({
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("analyst@chargebackos.demo");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const res = await loginRequest(email.trim().toLowerCase(), password);
      setToken(res.token);
      await navigate({ to: "/" });
    } catch (ex) {
      setErr(ex instanceof OpsApiError ? ex.message : "Sign-in failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid min-h-dvh place-items-center bg-bg px-4">
      <Card className="w-full max-w-md p-8">
        <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-accent">ChargebackOS</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-fg">Staff sign-in</h1>
        <p className="mt-2 text-[14px] font-medium text-muted">
          Defense-only demo. Seeded staff accounts only. Not a customer portal.
        </p>
        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <label className="block text-[13px] font-medium text-muted">
            Email
            <Input
              className="mt-1"
              type="email"
              required
              maxLength={320}
              value={email}
              autoComplete="username"
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label className="block text-[13px] font-medium text-muted">
            Password
            <Input
              className="mt-1"
              type="password"
              required
              maxLength={1024}
              value={password}
              autoComplete="current-password"
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {err ? <p role="alert" className="text-[13px] font-medium text-danger">{err}</p> : null}
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
