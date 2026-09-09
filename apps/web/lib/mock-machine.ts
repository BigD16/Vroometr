/** Static dashboard placeholders until maintenance and ride data are implemented. */

export const mockUser = {
  initials: "DG",
  displayName: "Drake Griffin",
  planLabel: "PRO",
};

export const mockMachine = {
  engineHours: "42.7",
  hoursSinceService: "6.2",
  lastRide: "AUG 20",
  healthPercent: 82,
  healthLabel: "GOOD",
  healthNote: "1 item needs attention",
  statusKicker: "MACHINE STATUS",
  statusTitle: "READY TO RIDE",
  statusDetail: "All critical systems look good.",
};

export const mockUpNext = [
  {
    title: "Clean & oil air filter",
    detail: "Due now · Last ride was dusty",
    due: null as string | null,
    urgent: true,
  },
  {
    title: "Transmission oil",
    detail: "Changed at 36.5 hrs",
    due: "2.3 HRS",
    urgent: false,
  },
  {
    title: "Chain & sprockets",
    detail: "Routine inspection",
    due: "NEXT RIDE",
    urgent: false,
  },
];

export const mockPlannedRide = {
  day: "29",
  month: "AUG",
  name: "Glen Helen",
  detail: "Saturday · 8:00 AM · 3.0 hrs",
};
