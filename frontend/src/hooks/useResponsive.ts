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
