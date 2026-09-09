export type BikeSummary = {
  id: string;
  nickname: string;
  make: string;
  model: string;
  year: number;
  stroke_type: "2T" | "4T";
  status: "active" | "inactive" | "archive";
};

export type ActiveBikeSnapshot = {
  bikes: BikeSummary[];
  activeBikeId: string | null;
  error: string | null;
};
