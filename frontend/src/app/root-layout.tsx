import { useEffect } from 'react';
import { THEME_PRESETS } from '@/lib/themes';

interface RootLayoutProps {
  children: React.ReactNode;
}

export function RootLayout({ children }: RootLayoutProps) {
  useEffect(() => {
    document.title = 'FastAPI Template';
  }, []);

  return <div data-theme-presets={THEME_PRESETS.length} className="antialiased">{children}</div>;
}