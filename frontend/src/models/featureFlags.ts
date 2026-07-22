export const Feature = {
  ExampleFlag: 'example_flag',
} as const;

export type FeatureFlagKey = (typeof Feature)[keyof typeof Feature];
