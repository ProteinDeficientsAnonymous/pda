export const Feature = {
  HostAttendanceReport: 'host_attendance_report',
  AdminAttendanceAnalytics: 'admin_attendance_analytics',
} as const;

export type FeatureFlagKey = (typeof Feature)[keyof typeof Feature];
