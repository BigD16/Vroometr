export type BikeStatus = "active" | "inactive" | "archive";
export type BikeType = "motorcycle" | "dirt_bike";
export type StrokeType = "2T" | "4T";
export type UnitPreference = "imperial" | "metric";

export type Bike = {
  id: string;
  user_id: string;
  nickname: string;
  make: string;
  model: string;
  year: number;
  displacement: number;
  bike_type: BikeType;
  stroke_type: StrokeType;
  purchase_date: string | null;
  engine_hours_at_purchase: number | null;
  current_engine_hours: number | null;
  current_engine_hours_is_estimated: boolean;
  status: BikeStatus;
  unit_preference: UnitPreference;
  selected_garage_scene_id: string | null;
  created_at: string;
  updated_at: string;
};

export type BikeSummary = Pick<
  Bike,
  "id" | "nickname" | "make" | "model" | "year" | "stroke_type" | "status"
>;

export type ActiveBikeSnapshot = {
  bikes: Bike[];
  activeBikeId: string | null;
  error: string | null;
};
