"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

type User = {
  id: string;
  email: string;
  name: string;
};

type WorkshopItem = {
  id: string;
  name: string;
  api_key_prefix: string;
  tier: string;
  created_at: string | null;
};

type UserContextType = {
  user: User | null;
  jwt: string | null;
  workshops: WorkshopItem[];
  login: (jwt: string, user: User, workshops: WorkshopItem[]) => void;
  logout: () => void;
  setWorkshops: (workshops: WorkshopItem[]) => void;
  loaded: boolean;
};

const UserContext = createContext<UserContextType>({
  user: null,
  jwt: null,
  workshops: [],
  login: () => {},
  logout: () => {},
  setWorkshops: () => {},
  loaded: false,
});

function parseJwt(token: string): User | null {
  try {
    const base64 = token.split(".")[1];
    const payload = JSON.parse(atob(base64));
    return {
      id: payload.sub,
      email: payload.email || "",
      name: payload.name || "",
    };
  } catch {
    return null;
  }
}

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [jwt, setJwt] = useState<string | null>(null);
  const [workshops, setWorkshops] = useState<WorkshopItem[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("retromind_jwt");
    if (stored) {
      const parsed = parseJwt(stored);
      if (parsed) {
        setJwt(stored);
        setUser(parsed);
      } else {
        localStorage.removeItem("retromind_jwt");
      }
    }
    setLoaded(true);
  }, []);

  const login = useCallback((token: string, userData: User, ws: WorkshopItem[]) => {
    localStorage.setItem("retromind_jwt", token);
    setJwt(token);
    setUser(userData);
    setWorkshops(ws);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("retromind_jwt");
    setJwt(null);
    setUser(null);
    setWorkshops([]);
  }, []);

  return (
    <UserContext.Provider value={{ user, jwt, workshops, login, logout, setWorkshops, loaded }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}
