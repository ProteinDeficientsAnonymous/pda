import { isValidElement } from 'react';
import type { RouteObject } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { AppShell } from '@/layout/AppShell';

import { router } from './routes';

function ancestorsOf(
  path: string,
  routes: RouteObject[],
  trail: RouteObject[] = [],
): RouteObject[] | null {
  for (const route of routes) {
    if (route.path === path) return trail;
    const found = route.children ? ancestorsOf(path, route.children, [...trail, route]) : null;
    if (found) return found;
  }
  return null;
}

function rendersAppShell(route: RouteObject) {
  return isValidElement(route.element) && route.element.type === AppShell;
}

function countPath(path: string, routes: RouteObject[]): number {
  return routes.reduce(
    (n, route) =>
      n + (route.path === path ? 1 : 0) + (route.children ? countPath(path, route.children) : 0),
    0,
  );
}

describe('routes', () => {
  it('renders the connect consent screen outside the app shell', () => {
    const ancestors = ancestorsOf('/connect/authorize', router.routes);
    expect(ancestors).not.toBeNull();
    expect(ancestors?.some(rendersAppShell)).toBe(false);
  });

  it('defines the connect consent route once', () => {
    expect(countPath('/connect/authorize', router.routes)).toBe(1);
  });

  it('still renders settings inside the app shell', () => {
    expect(ancestorsOf('/settings', router.routes)?.some(rendersAppShell)).toBe(true);
  });
});
