import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach, vi } from 'vitest';

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

globalThis.ResizeObserver = ResizeObserverMock;

if (typeof Element !== 'undefined' && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = vi.fn();
}

if (typeof URL !== 'undefined') {
  URL.createObjectURL = vi.fn(() => 'blob:terraqora-preview');
  URL.revokeObjectURL = vi.fn();
}

beforeEach(() => {
  localStorage.clear();
  if (typeof window !== 'undefined') {
    window.print = vi.fn();
  }
  // Fail fast to offline demo sandbox during Vitest runs unless a test overrides fetch.
  globalThis.fetch = vi.fn(() =>
    Promise.reject(new TypeError('Offline unit test sandbox'))
  ) as unknown as typeof fetch;
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
