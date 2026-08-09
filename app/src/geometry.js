export const DEFAULT_GEOMETRY = {
  mass_kg: 1500,
  velocity_kmh: 56,
  angle_deg: 0,
  a_pillar_thickness_mm: 1.2,
  crumple_zone_length_m: 0.8,
  yield_strength_mpa: 400,
  section_height_mm: 150,
  section_width_mm: 100,
  vehicle_class: 'sedan',
  test_type: 'frontal',
  year: 2020
}

export const FIELD_DEFS = [
  { key: 'mass_kg', label: 'Vehicle mass', unit: 'kg', min: 500, max: 4000, step: 50 },
  { key: 'velocity_kmh', label: 'Impact velocity', unit: 'km/h', min: 10, max: 120, step: 2 },
  { key: 'angle_deg', label: 'Impact angle', unit: 'deg', min: 0, max: 90, step: 1 },
  { key: 'a_pillar_thickness_mm', label: 'A-pillar thickness', unit: 'mm', min: 0.6, max: 3.0, step: 0.05 },
  { key: 'crumple_zone_length_m', label: 'Crumple zone length', unit: 'm', min: 0.4, max: 1.5, step: 0.02 },
  { key: 'yield_strength_mpa', label: 'Yield strength', unit: 'MPa', min: 250, max: 900, step: 10 },
  { key: 'section_height_mm', label: 'Section height', unit: 'mm', min: 90, max: 240, step: 5 },
  { key: 'section_width_mm', label: 'Section width', unit: 'mm', min: 70, max: 180, step: 5 }
]

export const CLASSES = ['sedan', 'suv', 'truck', 'ev']
export const TEST_TYPES = ['frontal', 'side', 'rollover']
export const YEARS = Array.from({ length: 25 }, (_, i) => 2024 - i)
