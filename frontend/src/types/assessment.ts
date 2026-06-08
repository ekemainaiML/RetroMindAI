"use client";

export interface VehicleClassification {
  type: string;
  confidence: number;
  classifier: string;
  human_confirmed?: boolean;
  alternatives?: Array<{ vehicle_type: string; confidence: number }>;
}

export interface ConfidenceFactors {
  quality: number;
  geometry: number;
  visibility: number;
  completeness: number;
  classification: number;
  deviation_certainty: number;
}

export interface RiskItem {
  severity: "low" | "medium" | "high" | "critical";
  category: string;
  message: string;
  description?: string;
}

export interface Deviation {
  component: string;
  severity: "low" | "medium" | "high" | "critical";
  description: string;
  reference?: number;
  estimated?: number;
  delta?: number;
  delta_pct?: number;
}

export interface Recommendation {
  title: string;
  priority: "essential" | "recommended" | "optional";
  category: string;
  description: string;
  rationale: string[];
  blocking: boolean;
  cost_estimate: {
    min: number;
    max: number;
    currency: string;
  };
  estimated_days: number;
  depends_on: string[];
}

export interface RiskSummary {
  system_risk_state: string;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
}

export interface ConfirmationRequired {
  type: string;
  message: string;
  options?: string[];
  current_value?: string;
}

export interface SimilarRetrofit {
  vehicle_id: string;
  type: string;
  matching_deviations: number;
  confidence: number;
}

export interface VehicleDimensions {
  length: number;
  width: number;
  height: number;
}

export interface Deviation3D {
  parameter: string;
  location: string;
  severity: string;
  delta_pct: number;
  color: string;
}

export interface RetrofitComponent3D {
  id: string;
  label: string;
  position: { x: number; y: number; z: number };
  color: string;
  size: { w: number; h: number; d: number };
}

export interface ViewAngles {
  default_camera: { theta: number; phi: number; radius: number };
}

export interface BatteryFitment {
  zone_id: string;
  label: string;
  position: { x: number; y: number; z: number };
  size: { w: number; h: number; d: number };
  clearance: {
    front: number;
    rear: number;
    left: number;
    right: number;
    top: number;
    bottom: number;
  };
  fitment_status: string;
}

export interface Measurement {
  id: string;
  start: { x: number; y: number; z: number };
  end: { x: number; y: number; z: number };
  distance: number;
}

export interface ThermalZone {
  id: string;
  label: string;
  position: { x: number; y: number; z: number };
  radius: number;
  severity: "low" | "medium" | "high";
  temperature_c: number;
  source: string;
}

export interface Waypoint3D {
  x: number;
  y: number;
  z: number;
}

export interface WiringRoute3D {
  id: string;
  label: string;
  waypoints: Waypoint3D[];
  color: string;
  caution_zones: string[];
  confidence: number;
}

export interface DigitalTwinData {
  vehicle_type: string;
  dimensions: VehicleDimensions;
  deviations_3d: Deviation3D[];
  retrofit_components: RetrofitComponent3D[];
  battery_fitment?: BatteryFitment;
  thermal_zones?: ThermalZone[];
  wiring_routes?: WiringRoute3D[];
  view_angles: ViewAngles;
}

export interface AssessmentData {
  assessment_state:
    | "feasible"
    | "conditional"
    | "reduced_confidence"
    | "inconclusive"
    | "not_feasible"
    | string;
  feasibility_score: number;
  feasibility_label: string;
  confidence_score: number;
  vehicle_classification?: VehicleClassification;
  confidence_factors?: ConfidenceFactors;
  risk_register?: RiskItem[];
  deviations?: Deviation[];
  recommendations?: Recommendation[];
  risk_summary?: RiskSummary;
  needs_confirmation: boolean;
  confirmation_required?: ConfirmationRequired;
  similar_retrofits?: SimilarRetrofit[];
  digital_twin?: DigitalTwinData;
  enhanced_views?: EnhancedViewEntry[];
  degradations?: Array<{
    component?: string;
    service?: string;
    severity?: string;
    fallback?: string;
    message?: string;
    tier?: number;
  }>;
}

export interface EnhancedViewEntry {
  view: string;
  original_url: string;
  enhanced_url: string;
}

export const SLOT_LABELS: Record<string, string> = {
  left_side_profile: "Left Side Profile",
  right_side_profile: "Right Side Profile",
  front_view: "Front View",
  rear_view: "Rear View",
  engine_bay: "Engine Bay",
  underbody: "Underbody",
};

export const ASSESSMENT_STATE_LABELS: Record<string, string> = {
  feasible: "Feasible",
  conditional: "Conditional",
  full_confidence: "Full Confidence",
  reduced_confidence: "Reduced Confidence",
  partial_assessment: "Partial Assessment",
  unsafe_to_assess: "Unsafe to Assess",
  inconclusive: "Inconclusive",
  not_feasible: "Not Feasible",
};

export const ASSESSMENT_STATE_COLORS: Record<string, string> = {
  feasible: "bg-green-100 text-green-800 border-green-300 dark:bg-green-900 dark:text-green-200 dark:border-green-700",
  conditional:
    "bg-yellow-100 text-yellow-800 border-yellow-300 dark:bg-yellow-900 dark:text-yellow-200 dark:border-yellow-700",
  full_confidence:
    "bg-green-100 text-green-800 border-green-300 dark:bg-green-900 dark:text-green-200 dark:border-green-700",
  reduced_confidence:
    "bg-orange-100 text-orange-800 border-orange-300 dark:bg-orange-900 dark:text-orange-200 dark:border-orange-700",
  partial_assessment:
    "bg-yellow-100 text-yellow-800 border-yellow-300 dark:bg-yellow-900 dark:text-yellow-200 dark:border-yellow-700",
  unsafe_to_assess:
    "bg-red-100 text-red-800 border-red-300 dark:bg-red-900 dark:text-red-200 dark:border-red-700",
  inconclusive:
    "bg-red-100 text-red-800 border-red-300 dark:bg-red-900 dark:text-red-200 dark:border-red-700",
  not_feasible:
    "bg-red-100 text-red-800 border-red-300 dark:bg-red-900 dark:text-red-200 dark:border-red-700",
};

export const STAGE_LABELS: Record<string, string> = {
  intake: "Uploading and validating vehicle imagery...",
  vehicle_classification: "Running vehicle classification...",
  geometry_extraction: "Extracting vehicle geometry...",
  deviation_detection: "Detecting deviations from OEM specifications...",
  confidence_scoring: "Calculating confidence scores...",
  recommendations: "Generating retrofit recommendations...",
  digital_twin: "Building 3D digital twin visualization...",
};

export const FEASIBILITY_LABELS: Record<string, string> = {
  feasible: "Feasible",
  feasible_with_adaptation: "Feasible with Adaptation",
  conditionally_feasible: "Conditionally Feasible",
  not_feasible: "Not Feasible",
};

export interface OEMSearchResult {
  id: string;
  manufacturer_id: string;
  manufacturer_name: string;
  model_name: string;
  generation?: string | null;
  vehicle_type: string;
  year_start?: number | null;
  year_end?: number | null;
}

export interface OEMSearchResponse {
  models: OEMSearchResult[];
  total: number;
}

export interface IdentifyVehicleResponse {
  intake_id: string;
  classification: {
    vehicle_type: string;
    confidence: number;
    alternatives: Array<{ type: string; confidence: number }>;
    model_loaded: boolean;
    classifier_used: string;
  };
  suggestions: OEMSearchResult[];
}
