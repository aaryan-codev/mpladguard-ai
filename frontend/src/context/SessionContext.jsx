import { createContext, useContext, useMemo, useState } from 'react';

const SessionContext = createContext(null);

const STORAGE_KEY = 'mpladguard_session';

function loadStored() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function SessionProvider({ children }) {
  const [session, setSession] = useState(loadStored);

  const value = useMemo(
    () => ({
      session,
      login: (username, role) => {
        const next = { username, role };
        setSession(next);
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      },
      logout: () => {
        setSession(null);
        sessionStorage.removeItem(STORAGE_KEY);
      },
    }),
    [session]
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession must be used within a SessionProvider');
  return ctx;
}
