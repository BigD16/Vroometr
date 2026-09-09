"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";

import { readApiError } from "@/lib/api-errors";
import type { ActiveBikeSnapshot, Bike } from "@/lib/bikes";

type LoadState = "loading" | "ready" | "error";

type ActiveBikeContextValue = {
  bikes: Bike[];
  activeBike: Bike | null;
  state: LoadState;
  isSaving: boolean;
  error: string | null;
  selectBike: (bikeId: string) => Promise<boolean>;
  reload: () => Promise<void>;
};

const ActiveBikeContext = createContext<ActiveBikeContextValue | null>(null);

export function ActiveBikeProvider({
  children,
  initial,
}: {
  children: ReactNode;
  initial: ActiveBikeSnapshot;
}) {
  const [bikes, setBikes] = useState<Bike[]>(initial.bikes);
  const [activeBikeId, setActiveBikeId] = useState<string | null>(initial.activeBikeId);
  const [state, setState] = useState<LoadState>(initial.error === null ? "ready" : "error");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(initial.error);

  const reload = useCallback(async () => {
    setState("loading");
    setError(null);
    try {
      const [bikesResponse, activeResponse] = await Promise.all([
        fetch("/api/bikes", { cache: "no-store" }),
        fetch("/api/me/active-bike", { cache: "no-store" }),
      ]);
      if (!bikesResponse.ok) {
        throw new Error(await readApiError(bikesResponse, "Bike context is unavailable"));
      }
      if (!activeResponse.ok) {
        throw new Error(await readApiError(activeResponse, "Bike context is unavailable"));
      }
      const loadedBikes = (await bikesResponse.json()) as Bike[];
      const active = (await activeResponse.json()) as { active_bike_id: string | null };
      setBikes(loadedBikes);
      setActiveBikeId(active.active_bike_id);
      setState("ready");
    } catch (caught) {
      setState("error");
      setError(caught instanceof Error ? caught.message : "Bike context is unavailable");
    }
  }, []);

  const selectBike = useCallback(async (bikeId: string) => {
    setIsSaving(true);
    setError(null);
    try {
      const response = await fetch("/api/me/active-bike", {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ bike_id: bikeId }),
      });
      if (!response.ok) {
        throw new Error(await readApiError(response, "Could not change active bike"));
      }
      const active = (await response.json()) as { active_bike_id: string };
      setActiveBikeId(active.active_bike_id);
      return true;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not change active bike");
      return false;
    } finally {
      setIsSaving(false);
    }
  }, []);

  const value = useMemo<ActiveBikeContextValue>(
    () => ({
      bikes,
      activeBike: bikes.find((bike) => bike.id === activeBikeId) ?? null,
      state,
      isSaving,
      error,
      selectBike,
      reload,
    }),
    [activeBikeId, bikes, error, isSaving, reload, selectBike, state],
  );

  return <ActiveBikeContext.Provider value={value}>{children}</ActiveBikeContext.Provider>;
}

export function useActiveBike(): ActiveBikeContextValue {
  const context = useContext(ActiveBikeContext);
  if (context === null) {
    throw new Error("useActiveBike must be used inside ActiveBikeProvider");
  }
  return context;
}
