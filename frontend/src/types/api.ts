export type UserRole = 'farmer' | 'admin';
export type SupportedLanguage = 'en' | 'ta' | 'ml' | 'hi' | 'te';
export type DataSourceMode = 'live_api' | 'demo_preview';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  preferred_language: SupportedLanguage;
  is_active: boolean;
  created_at: string;
}

export interface FarmerProfile {
  id: string;
  user_id: string;
  phone: string | null;
  state: string | null;
  district: string | null;
  experience_years: number | null;
  primary_soil_type: string | null;
  preferred_units: 'metric' | 'imperial';
  preferred_language?: SupportedLanguage;
}

export interface Farm {
  id: string;
  user_id: string;
  name: string;
  state: string;
  district: string | null;
  latitude: number | null;
  longitude: number | null;
  area_hectares: number;
  soil_type: string | null;
  soil_ph: number | null;
  irrigation_type: 'rainfed' | 'drip' | 'sprinkler' | 'canal' | 'borewell' | 'mixed' | null;
  primary_crop: string | null;
  created_at: string;
  updated_at?: string;
}

export type FarmPayload = Omit<Farm, 'id' | 'user_id' | 'created_at' | 'updated_at'>;
export type FarmUpdatePayload = Partial<FarmPayload>;

export interface AuthSession {
  access_token: string;
  token_type: string;
  user: User;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  preferred_language: SupportedLanguage;
  state?: string;
}

export interface CropYieldRequest {
  farm_id?: string | null;
  crop: string;
  crop_year: number;
  season: string;
  state: string;
  area_hectares: number;
  annual_rainfall_mm: number;
  fertilizer_kg: number;
  pesticide_kg: number;
}

export interface FeatureDriver {
  feature: string;
  impact_pct: number;
  direction: 'positive' | 'negative' | 'neutral';
}

export interface CropYieldResponse {
  id: string;
  farm_id?: string | null;
  crop: string;
  state: string;
  season: string;
  crop_year: number;
  area_hectares: number;
  predicted_yield: number;
  yield_unit: string;
  estimated_total_production: number;
  production_unit: string;
  model_name: string;
  model_version: string;
  feature_drivers: FeatureDriver[];
  advisory_note: string;
  created_at: string;
  source_mode: DataSourceMode;
}

export interface DiseaseCandidate {
  label: string;
  confidence: number;
}

export interface DiseaseDetectionResponse {
  id: string;
  farm_id?: string | null;
  crop_hint?: string | null;
  image_filename: string;
  predicted_label: string;
  crop_name: string;
  disease_name: string;
  is_healthy: boolean;
  confidence: number;
  top2_margin?: number | null;
  is_uncertain: boolean;
  uncertainty_reason: string | null;
  top_predictions: DiseaseCandidate[];
  treatment_summary: string;
  prevention_notes: string;
  next_steps?: string[];
  limitations?: string[];
  supported_scope_note?: string;
  model_version: string;
  created_at: string;
  source_mode: DataSourceMode;
}

export interface FertilizerRequest {
  farm_id?: string | null;
  nitrogen: number;
  phosphorus: number;
  potassium: number;
  soil_ph: number;
  soil_type: string;
  crop_type: string;
  location?: string | null;
}

export interface NutrientLevel {
  nutrient: string;
  value: number;
  optimal_min: number;
  optimal_max: number;
  status: 'low' | 'optimal' | 'high';
}

export interface FertilizerResponse {
  id: string;
  farm_id?: string | null;
  nitrogen?: number;
  phosphorus?: number;
  potassium?: number;
  soil_ph?: number;
  soil_type?: string;
  crop_type?: string;
  location?: string | null;
  recommended_fertilizer: string;
  confidence: number;
  ml_predicted_grade?: string | null;
  recommendation_mode?:
    | 'ml_grade_with_agronomic_guardrails'
    | 'agronomic_sufficiency_guardrail';
  dataset_coverage_note?: string;
  nutrient_levels: NutrientLevel[];
  ph_assessment: string;
  advisory_notes: string;
  expert_disclaimer: string;
  model_version: string;
  created_at: string;
  source_mode: DataSourceMode;
}

export interface CropRecommendationRequest {
  farm_id?: string | null;
  nitrogen: number;
  phosphorus: number;
  potassium: number;
  temperature_c: number;
  humidity_pct: number;
  soil_ph: number;
  rainfall_mm: number;
  season?: string | null;
  region?: string | null;
}

export interface CropCandidate {
  crop: string;
  probability: number;
  fit_reason: string;
}

export interface CropRecommendationResponse {
  id: string;
  farm_id?: string | null;
  nitrogen?: number;
  phosphorus?: number;
  potassium?: number;
  temperature_c?: number;
  humidity_pct?: number;
  soil_ph?: number;
  rainfall_mm?: number;
  season?: string | null;
  region?: string | null;
  recommended_crop: string;
  top_candidates: CropCandidate[];
  soil_climate_summary: string;
  model_version: string;
  created_at: string;
  source_mode: DataSourceMode;
}

export interface WeatherIrrigationRequest {
  farm_id?: string | null;
  location_name?: string;
  latitude?: number;
  longitude?: number;
  crop_type?: string;
  growth_stage?: 'initial' | 'development' | 'mid_season' | 'late_season' | 'unknown';
  soil_type?: string | null;
  irrigation_type?: 'rainfed' | 'drip' | 'sprinkler' | 'canal' | 'borewell' | 'mixed' | null;
  soil_moisture_pct?: number | null;
}

export interface DailyForecastPoint {
  date: string;
  temp_max_c: number;
  temp_min_c: number;
  humidity_pct: number;
  rain_mm: number;
  precipitation_probability_pct?: number | null;
  et0_mm: number;
}

export interface WeatherAlert {
  severity: 'info' | 'warning' | 'alert';
  title: string;
  message: string;
}

export interface WeatherIrrigationResponse {
  id: string;
  saved_to_history?: boolean;
  farm_id?: string | null;
  location_name: string;
  latitude: number;
  longitude: number;
  crop_type?: string | null;
  growth_stage?: string | null;
  soil_type?: string | null;
  irrigation_type?: string | null;
  weather_provider: string;
  provider_attribution?: string;
  observation_time?: string;
  forecast_generated_at?: string;
  observation_age_minutes?: number;
  freshness_status?: 'live' | 'cached' | 'delayed';
  cache_hit?: boolean;
  units_summary?: Record<string, string>;
  current_temp_c: number;
  current_humidity_pct: number;
  wind_speed_kmh: number;
  weather_condition: string;
  forecast_rainfall_7d_mm: number;
  estimated_et0_mm: number;
  recommended_water_mm: number | null;
  schedule_status?: 'computed' | 'insufficient_agronomic_inputs' | 'rainfed_advisory';
  irrigation_urgency:
    | 'low'
    | 'moderate'
    | 'high'
    | 'skip_rain_expected'
    | 'insufficient_data';
  is_sensor_backed: boolean;
  sensor_notice: string;
  missing_inputs?: string[];
  assumptions?: string[];
  advisory_notes: string;
  alerts: WeatherAlert[];
  forecast_7d: DailyForecastPoint[];
  created_at: string;
  source_mode: DataSourceMode;
}

export type ChatLanguageChoice = SupportedLanguage | 'auto';

export interface ChatSession {
  id: string;
  title: string;
  language: SupportedLanguage;
  farm_id: string | null;
  message_count?: number;
  created_at?: string;
  updated_at: string;
}

export interface ChatCitation {
  source_title: string;
  section: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations: ChatCitation[];
  provider: string | null;
  model_name: string | null;
  latency_ms?: number | null;
  detected_language?: SupportedLanguage | null;
  created_at: string;
}

export interface ChatTurnResult {
  session?: ChatSession;
  userMsg: ChatMessage;
  assistantMsg: ChatMessage;
  resolvedLanguage?: SupportedLanguage;
  autoDetected?: boolean;
}

export interface AnalyticsFilter {
  crop?: string;
  state?: string;
  season?: string;
  year_start?: number;
  year_end?: number;
}

export interface AnalyticsResponse {
  total_records: number;
  unique_crops: number;
  unique_states: number;
  avg_yield: number;
  avg_rainfall_mm: number;
  total_fertilizer_tonnes: number;
  total_pesticide_tonnes: number;
  crop_distribution: Array<{ name: string; records: number; avg_yield: number }>;
  state_production: Array<{ state: string; production_mt: number; records: number }>;
  annual_trends: Array<{
    year: number;
    avg_rainfall: number;
    avg_yield: number;
    fertilizer_index: number;
    pesticide_index: number;
  }>;
  yield_comparison: Array<{ crop: string; kharif: number; rabi: number; whole_year: number }>;
  correlation_matrix: Array<{ feature_x: string; feature_y: string; correlation: number }>;
  source_mode: DataSourceMode;
}

export interface ReportCreateRequest {
  title: string;
  farm_id?: string | null;
  crop: string;
  state: string;
  season: string;
  area_hectares: number;
  predicted_yield: number;
  yield_unit: string;
  fertilizer_recommendation: string;
  irrigation_summary: string;
  language: SupportedLanguage;
}

export interface GeneratedReport {
  id: string;
  title: string;
  crop: string;
  state: string;
  season: string;
  area_hectares: number;
  predicted_yield: number;
  yield_unit: string;
  model_explanation: string;
  agricultural_observations: string[];
  fertilizer_recommendation: string;
  irrigation_summary: string;
  ai_summary: string;
  pdf_filename: string;
  created_at: string;
  source_mode: DataSourceMode;
}

export interface AdminUserItem {
  id: string;
  full_name: string;
  email: string;
  role: UserRole;
  preferred_language: SupportedLanguage;
  is_active: boolean;
  farms_count: number;
  predictions_count: number;
  created_at: string;
}

export interface AdminOverviewResponse {
  total_users: number;
  active_farms: number;
  total_predictions: number;
  total_disease_scans: number;
  total_ai_chats: number;
  models: Array<{
    module: string;
    algorithm: string;
    status: string;
    metric_label: string;
    metric_value: string;
    artifact_size: string;
  }>;
  users: AdminUserItem[];
  source_mode: DataSourceMode;
}
