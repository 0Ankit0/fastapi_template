'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/store/auth-store';
import {
  ArrowRight,
  CheckCircle2,
  CreditCard,
  Layers3,
  LockKeyhole,
  Rocket,
  ShieldCheck,
  Sparkles,
  Workflow,
} from 'lucide-react';

const heroPillars = [
  {
    icon: Layers3,
    title: 'Postgres-only foundation',
    description: 'SQLAlchemy models, Alembic migrations, and async sessions are already wired for the one database path that matters.',
  },
  {
    icon: LockKeyhole,
    title: 'Security-first defaults',
    description: 'Authentication, token tracking, RBAC, audit hooks, and tenant-aware permissions ship as the starting point.',
  },
  {
    icon: Sparkles,
    title: 'Launch-ready interface',
    description: 'A typed Next.js app shell, auth routes, dashboards, and settings flows are in place before product work begins.',
  },
];

const platformHighlights = [
  {
    icon: ShieldCheck,
    title: 'Identity and access built in',
    description: 'Sign up, sign in, OTP verification, role management, and observability flows are already represented in the template.',
  },
  {
    icon: CreditCard,
    title: 'Business workflows included',
    description: 'Payments, notifications, multitenancy, and finance primitives are scaffolded so new projects start from features, not placeholders.',
  },
  {
    icon: Workflow,
    title: 'Operational backbone ready',
    description: 'Celery workers, Redis, container health checks, and environment-driven configuration are connected end to end.',
  },
];

const foundationStats = [
  { value: 'Postgres', label: 'single database target' },
  { value: 'SQLAlchemy', label: 'ORM and migrations' },
  { value: 'Next.js', label: 'typed UI shell' },
];

const launchChecklist = [
  'FastAPI + SQLAlchemy + Alembic',
  'PostgreSQL-only data layer',
  'Next.js app router and auth flows',
  'Redis-backed workers and queues',
  'Multitenant RBAC and notifications',
  'Containerized local development',
];

const primaryLinkClass =
  'inline-flex items-center justify-center gap-2 rounded-full bg-slate-950 px-6 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400';

const secondaryLinkClass =
  'inline-flex items-center justify-center gap-2 rounded-full border border-slate-300 bg-white/75 px-6 py-3 text-sm font-semibold text-slate-900 shadow-sm transition hover:border-slate-400 hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-300';

export default function Home() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      router.replace('/dashboard');
    }
  }, [isAuthenticated, router]);

  return (
    <div className="min-h-screen overflow-x-hidden bg-[linear-gradient(180deg,#f8fbff_0%,#eef4ff_42%,#ffffff_100%)] text-slate-950">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[34rem] bg-[radial-gradient(circle_at_top_left,rgba(37,99,235,0.2),transparent_34%),radial-gradient(circle_at_top_right,rgba(14,165,233,0.16),transparent_30%)]" />

      <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/80 backdrop-blur-xl">
        <div className="mx-auto flex h-20 max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-3" aria-label="FastAPI Template home">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-950 text-base font-semibold text-white shadow-lg shadow-slate-900/15">
              F
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-600">FastAPI</p>
              <p className="text-lg font-semibold text-slate-950">Template</p>
            </div>
          </Link>

          <nav className="flex items-center gap-3 sm:gap-4">
            <Link href="/login" className="text-sm font-medium text-slate-700 transition hover:text-slate-950">
              Sign in
            </Link>
            <Link href="/signup" className={`${primaryLinkClass} px-5 py-2.5`}>
              Get started
            </Link>
          </nav>
        </div>
      </header>

      <main className="relative">
        <section className="px-4 pb-20 pt-14 sm:px-6 lg:px-8 lg:pb-28 lg:pt-20">
          <div className="mx-auto grid max-w-6xl gap-14 lg:grid-cols-[minmax(0,1.1fr)_minmax(360px,0.9fr)] lg:items-center">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-sky-200 bg-white/80 px-4 py-2 text-sm font-medium text-slate-700 shadow-sm backdrop-blur">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                Ready for new product work on day one
              </div>

              <h1 className="mt-6 max-w-3xl text-5xl font-semibold tracking-tight text-slate-950 sm:text-6xl">
                Ship on top of a real FastAPI architecture, not a cleanup backlog.
              </h1>

              <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600 sm:text-xl">
                FastAPI Template pairs a typed Next.js interface with a PostgreSQL-only backend,
                SQLAlchemy models, background workers, and security defaults that are already
                coherent across the stack.
              </p>

              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link href="/signup" className={`${primaryLinkClass} w-full px-7 py-3.5 text-base sm:w-auto`}>
                  Launch your project
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link href="/login" className={`${secondaryLinkClass} w-full px-7 py-3.5 text-base sm:w-auto`}>
                  Open the dashboard
                </Link>
              </div>

              <div className="mt-10 grid gap-4 sm:grid-cols-3">
                {foundationStats.map((stat) => (
                  <div
                    key={stat.label}
                    className="rounded-3xl border border-white/70 bg-white/75 px-5 py-4 shadow-sm shadow-slate-900/5 backdrop-blur"
                  >
                    <p className="text-lg font-semibold text-slate-950">{stat.value}</p>
                    <p className="mt-1 text-sm text-slate-600">{stat.label}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative">
              <div className="absolute inset-0 -z-10 rounded-[2rem] bg-[linear-gradient(135deg,rgba(15,23,42,0.96),rgba(30,41,59,0.88),rgba(37,99,235,0.84))] shadow-[0_30px_80px_rgba(15,23,42,0.24)]" />
              <div className="rounded-[2rem] border border-white/40 bg-white/10 p-6 backdrop-blur-xl">
                <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/25 p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.3em] text-sky-100/80">
                        Included in the template
                      </p>
                      <h2 className="mt-3 text-2xl font-semibold text-white">
                        A delivery surface that already fits production.
                      </h2>
                    </div>
                    <div className="rounded-2xl bg-white/10 p-3 text-sky-100">
                      <Rocket className="h-5 w-5" />
                    </div>
                  </div>

                  <div className="mt-6 space-y-4">
                    {heroPillars.map((pillar) => (
                      <div
                        key={pillar.title}
                        className="rounded-3xl border border-white/10 bg-white/6 px-5 py-4"
                      >
                        <div className="flex items-start gap-4">
                          <div className="mt-0.5 rounded-2xl bg-white/10 p-3 text-sky-100">
                            <pillar.icon className="h-5 w-5" />
                          </div>
                          <div>
                            <h3 className="text-base font-semibold text-white">{pillar.title}</h3>
                            <p className="mt-1 text-sm leading-6 text-slate-200/88">
                              {pillar.description}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="mt-6 grid gap-3 sm:grid-cols-2">
                    {launchChecklist.map((item) => (
                      <div
                        key={item}
                        className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/7 px-4 py-3 text-sm text-slate-100"
                      >
                        <CheckCircle2 className="h-4 w-4 shrink-0 text-sky-200" />
                        <span>{item}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="px-4 py-20 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-6xl">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
              <div className="max-w-3xl">
                <p className="text-sm font-semibold uppercase tracking-[0.3em] text-blue-600">
                  Built for repeatable delivery
                </p>
                <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
                  Core platform features without the template debt.
                </h2>
              </div>
              <p className="max-w-2xl text-base leading-7 text-slate-600 sm:text-lg">
                The goal is to remove the usual rewrite cycle. The backend, worker, data layer,
                and frontend shell all start from the same architectural decisions, so new work can
                stay focused on domain features.
              </p>
            </div>

            <div className="mt-10 grid gap-6 lg:grid-cols-3">
              {platformHighlights.map((highlight) => (
                <div
                  key={highlight.title}
                  className="rounded-[1.75rem] border border-slate-200/80 bg-white/85 p-7 shadow-[0_18px_45px_rgba(15,23,42,0.06)] backdrop-blur"
                >
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
                    <highlight.icon className="h-7 w-7" />
                  </div>
                  <h3 className="mt-6 text-xl font-semibold text-slate-950">{highlight.title}</h3>
                  <p className="mt-3 text-sm leading-7 text-slate-600 sm:text-base">
                    {highlight.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="px-4 pb-24 sm:px-6 lg:px-8">
          <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(320px,0.95fr)]">
            <div className="rounded-[2rem] bg-slate-950 px-8 py-10 text-white shadow-[0_30px_80px_rgba(15,23,42,0.18)] sm:px-10 sm:py-12">
              <p className="text-sm font-semibold uppercase tracking-[0.3em] text-sky-200/85">
                Start from something opinionated
              </p>
              <h2 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">
                Use the template as the base, not as the draft.
              </h2>
              <p className="mt-5 max-w-2xl text-base leading-8 text-slate-300 sm:text-lg">
                Stand up an internal platform, SaaS product, or customer portal with a stack that
                already reflects how the app should behave in development and production.
              </p>

              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link href="/signup" className="inline-flex items-center justify-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-semibold text-slate-950 transition hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70">
                  Create your account
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link href="/login" className="inline-flex items-center justify-center rounded-full border border-white/20 px-6 py-3 text-sm font-semibold text-white transition hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40">
                  Sign in instead
                </Link>
              </div>
            </div>

            <div className="rounded-[2rem] border border-slate-200/80 bg-white/90 p-8 shadow-[0_18px_45px_rgba(15,23,42,0.06)] backdrop-blur">
              <p className="text-sm font-semibold uppercase tracking-[0.3em] text-blue-600">
                What ships in the box
              </p>
              <h3 className="mt-4 text-2xl font-semibold text-slate-950">Template coverage across the stack.</h3>
              <div className="mt-6 space-y-4">
                {heroPillars.map((pillar) => (
                  <div key={pillar.title} className="rounded-3xl bg-slate-50 px-5 py-4">
                    <p className="text-sm font-semibold text-slate-950">{pillar.title}</p>
                    <p className="mt-1 text-sm leading-6 text-slate-600">{pillar.description}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200/80 px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} FastAPI Template. Built for new projects.</p>
          <p>Postgres-first. Typed frontend. Secure defaults.</p>
        </div>
      </footer>
    </div>
  );
}
