export const Feature = {
  ExampleFlag: 'example_flag',
  HostAttendanceReport: 'host_attendance_report',
} as const;

export type FeatureFlagKey = (typeof Feature)[keyof typeof Feature];
