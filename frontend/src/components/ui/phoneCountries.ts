import type { Country } from 'react-phone-number-input';

let restrictedCountries: Country[] | undefined;

export function getPhoneCountries(): Country[] | undefined {
  return restrictedCountries;
}

// Tests render PhoneField in ~6 suites; the full 245-option country <select>
// makes every render/keystroke/axe pass 10-88x slower and trips CI timeouts
// under parallel load. Narrowing the list in the test setup keeps production
// showing all countries while making the suite fast.
export function setPhoneCountriesForTesting(countries: Country[]): void {
  restrictedCountries = countries;
}
