import { useLayoutEffect } from 'react';

// the router doesn't reset scroll, so a short screen replacing a long form would open scrolled past its content
export function useScrollToTopOnMount(): void {
  useLayoutEffect(() => {
    window.scrollTo(0, 0);
  }, []);
}
