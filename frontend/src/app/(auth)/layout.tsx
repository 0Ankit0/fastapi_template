import { Link } from '@/lib/router';
import { CheckCircle2 } from 'lucide-react';

const authHighlights = [
  'Postgres-first backend with SQLAlchemy and Alembic',
  'Typed React + Vite frontend with shared auth flows',
  'RBAC, notifications, and background workers included',
];

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-shell-gradient relative min-h-screen overflow-hidden">
      <div className="app-shell-orbs pointer-events-none absolute inset-x-0 top-0 h-[36rem]" />

      <div className="relative mx-auto grid min-h-screen max-w-6xl gap-12 px-4 py-10 sm:px-6 lg:grid-cols-[minmax(0,1fr)_minmax(420px,460px)] lg:items-center lg:px-8">
        <div className="hidden max-w-xl lg:block">
          <Link href="/" className="inline-flex items-center gap-3" aria-label="FastAPI Template home">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-950 text-base font-semibold text-white shadow-lg shadow-slate-900/15">
              F
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-600">FastAPI</p>
              <p className="text-lg font-semibold text-slate-950">Template</p>
            </div>
          </Link>

          <div className="mt-10 space-y-6">
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-blue-600">
              Secure workspace access
            </p>
            <h1 className="text-5xl font-semibold tracking-tight text-slate-950">
              Sign in to a stack that already matches the production shape.
            </h1>
            <p className="text-lg leading-8 text-slate-600">
              Authentication sits on top of the same FastAPI, PostgreSQL, and React foundation
              as the rest of the template, so the first user flow feels like part of the platform.
            </p>
          </div>

          <div className="mt-8 space-y-4">
            {authHighlights.map((highlight) => (
              <div
                key={highlight}
                className="app-glass-panel flex items-center gap-3 rounded-2xl px-4 py-3 text-sm text-slate-700 shadow-sm"
              >
                <CheckCircle2 className="h-4 w-4 shrink-0 text-blue-600" />
                <span>{highlight}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-center">
          <div className="w-full max-w-md space-y-6">
            <Link href="/" className="inline-flex items-center gap-3 lg:hidden" aria-label="FastAPI Template home">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-950 text-base font-semibold text-white shadow-lg shadow-slate-900/15">
                F
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-600">FastAPI</p>
                <p className="text-lg font-semibold text-slate-950">Template</p>
              </div>
            </Link>

            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
