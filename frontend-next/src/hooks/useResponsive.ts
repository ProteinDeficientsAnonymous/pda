// Matches Flutter's MediaQuery.sizeOf(context).width >= 720 check used to
// decide side-panel vs full-page layouts. Updates on window resize.

import { useEffect, useState } from 'react';

export function useIsWideScreen(minWidth = 720): boolean {
  const [isWide, setIsWide] = useState(
    typeof window !== 'undefined' ? window.innerWidth >= minWidth : true,
  );
  useEffect(() => {
    const onResize = () => {
      setIsWide(window.innerWidth >= minWidth);
    };
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
    };
  }, [minWidth]);
  return isWide;
}
