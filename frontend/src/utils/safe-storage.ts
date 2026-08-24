import type { StateStorage } from 'zustand/middleware';

type StorageKind = 'local' | 'session';

function probe(store: Storage): boolean {
  try {
    const key = '__storage_test__';
    store.setItem(key, '1');
    store.removeItem(key);
    return true;
  } catch {
    return false;
  }
}

function memoryStorage(): StateStorage {
  const store = new Map<string, string>();
  return {
    getItem: (name) => store.get(name) ?? null,
    setItem: (name, value) => { store.set(name, value); },
    removeItem: (name) => { store.delete(name); },
  };
}

// Web storage throws outright in some privacy modes, so every access is guarded
export function createSafeStorage(kind: StorageKind): StateStorage {
  let store: Storage | null = null;
  try {
    store = kind === 'local' ? localStorage : sessionStorage;
  } catch {
    store = null;
  }
  if (!store || !probe(store)) return memoryStorage();

  const target = store;
  return {
    getItem: (name) => {
      try {
        return target.getItem(name);
      } catch {
        return null;
      }
    },
    setItem: (name, value) => {
      try {
        target.setItem(name, value);
      } catch {
        // In-memory state still works without persistence
      }
    },
    removeItem: (name) => {
      try {
        target.removeItem(name);
      } catch {
        // Nothing to recover
      }
    },
  };
}
