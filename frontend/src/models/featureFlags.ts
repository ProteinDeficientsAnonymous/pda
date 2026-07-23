export const Feature = {
  HostAttendanceReport: 'host_attendance_report',
  AdminAttendanceAnalytics: 'admin_attendance_analytics',
  EventPaymentConfirmation: 'event_payment_confirmation',
} as const;

export type FeatureFlagKey = (typeof Feature)[keyof typeof Feature];
