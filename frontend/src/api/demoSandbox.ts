import type {
  AdminOverviewResponse,
  AnalyticsFilter,
  AnalyticsResponse,
  AuthSession,
  ChatMessage,
  ChatSession,
  CropRecommendationRequest,
  CropRecommendationResponse,
  CropYieldRequest,
  CropYieldResponse,
  DiseaseDetectionResponse,
  Farm,
  FarmerProfile,
  FertilizerRequest,
  FertilizerResponse,
  GeneratedReport,
  ReportCreateRequest,
  SupportedLanguage,
  User,
  WeatherIrrigationRequest,
  WeatherIrrigationResponse,
} from '../types/api';

const makeId = (prefix: string) =>
  `${prefix}-${Math.random().toString(36).slice(2, 9)}`;

const DEMO_USERS: Record<string, User> = {
  farmer: {
    id: 'demo-farmer-001',
    email: 'ananya.farmer@terraqora.demo',
    full_name: 'Ananya Sundaram',
    role: 'farmer',
    preferred_language: 'en',
    is_active: true,
    created_at: '2026-09-12T08:00:00Z',
  },
  admin: {
    id: 'demo-admin-001',
    email: 'admin@terraqora.demo',
    full_name: 'Dr. Karthik Menon',
    role: 'admin',
    preferred_language: 'en',
    is_active: true,
    created_at: '2026-08-01T08:00:00Z',
  },
};

let demoProfile: FarmerProfile = {
  id: 'profile-001',
  user_id: 'demo-farmer-001',
  phone: '+91 98400 00123',
  state: 'Tamil Nadu',
  district: 'Coimbatore',
  experience_years: 9,
  primary_soil_type: 'Red Loamy',
  preferred_units: 'metric',
};

let demoFarms: Farm[] = [
  {
    id: 'farm-pollachi-01',
    user_id: 'demo-farmer-001',
    name: 'Pollachi North Plot A',
    state: 'Tamil Nadu',
    district: 'Coimbatore',
    latitude: 10.658,
    longitude: 77.008,
    area_hectares: 4.8,
    soil_type: 'Red Loamy',
    soil_ph: 6.4,
    irrigation_type: 'drip',
    primary_crop: 'Coconut',
    created_at: '2026-09-14T09:30:00Z',
  },
  {
    id: 'farm-cauvery-02',
    user_id: 'demo-farmer-001',
    name: 'Thanjavur Delta Block 2',
    state: 'Tamil Nadu',
    district: 'Thanjavur',
    latitude: 10.787,
    longitude: 79.1378,
    area_hectares: 3.2,
    soil_type: 'Alluvial',
    soil_ph: 6.8,
    irrigation_type: 'canal',
    primary_crop: 'Rice',
    created_at: '2026-09-20T11:15:00Z',
  },
];

let demoSessions: ChatSession[] = [
  {
    id: 'chat-session-01',
    title: 'Kharif Paddy Nutrient & Irrigation Check',
    language: 'en',
    farm_id: 'farm-cauvery-02',
    updated_at: new Date().toISOString(),
  },
];

let demoMessages: Record<string, ChatMessage[]> = {
  'chat-session-01': [
    {
      id: 'msg-01',
      session_id: 'chat-session-01',
      role: 'assistant',
      content:
        'Welcome to the TerraQora AI Farming Assistant (Preview Sandbox). In Phases 4–6, this assistant connects to Google Gemini with grounded agricultural RAG across English, Tamil, Malayalam, Hindi, and Telugu. Ask a question to preview the conversation workflow.',
      citations: [
        {
          source_title: 'TerraQora Agronomy Knowledge Base (Preview)',
          section: 'Kharif Paddy Best Practices',
        },
      ],
      provider: 'preview_sandbox',
      model_name: 'gemini-2.5-flash (pending backend)',
      created_at: new Date().toISOString(),
    },
  ],
};

let demoReports: GeneratedReport[] = [
  {
    id: 'rep-demo-01',
    title: 'Kharif 2026 Rice Acreage Advisory — Thanjavur Delta',
    crop: 'Rice',
    state: 'Tamil Nadu',
    season: 'Kharif',
    area_hectares: 3.2,
    predicted_yield: 3.84,
    yield_unit: 'tonnes/hectare',
    model_explanation:
      'Synthetic Phase 3 preview explanation: Yield estimate driven by state historical baseline, Kharif rainfall adequacy, and per-hectare fertilizer application intensity.',
    agricultural_observations: [
      'Estimated rainfall aligns with Kharif paddy establishment phase.',
      'Soil pH 6.8 falls within optimal nutrient bioavailability window (6.0–7.2).',
      'Weather-derived ET₀ estimate suggests delaying supplemental irrigation if rain exceeds 15 mm.',
    ],
    fertilizer_recommendation: 'Split Urea + DAP + MOP (Verify exact dose with local KVK soil test)',
    irrigation_summary: 'Moderate demand (~22 mm over 5 days; weather-estimated, not soil sensor reading).',
    ai_summary:
      'Preview Report Summary: Field conditions indicate favorable vegetative growth potential. Prioritize split nitrogen top-dressing and monitor leaf sheath health post-monsoon showers.',
    pdf_filename: 'TerraQora_Rice_TamilNadu_Preview.pdf',
    created_at: '2026-11-10T10:15:00Z',
    source_mode: 'demo_preview',
  },
];

let demoYieldHistory: CropYieldResponse[] = [];
let demoCropRecHistory: CropRecommendationResponse[] = [];
let demoFertilizerHistory: FertilizerResponse[] = [];

export const demoSandbox = {
  login(email: string, roleHint?: 'farmer' | 'admin'): AuthSession {
    const isAdmin = roleHint === 'admin' || email.toLowerCase().includes('admin');
    const user = isAdmin ? { ...DEMO_USERS.admin, email } : { ...DEMO_USERS.farmer, email };
    return {
      access_token: `demo.preview.token.${user.role}`,
      token_type: 'bearer',
      user,
    };
  },

  register(fullName: string, email: string, language: SupportedLanguage): AuthSession {
    const user: User = {
      id: makeId('demo-user'),
      email,
      full_name: fullName,
      role: 'farmer',
      preferred_language: language,
      is_active: true,
      created_at: new Date().toISOString(),
    };
    return {
      access_token: 'demo.preview.token.farmer',
      token_type: 'bearer',
      user,
    };
  },

  getProfile(): FarmerProfile {
    return { ...demoProfile };
  },

  updateProfile(patch: Partial<FarmerProfile>): FarmerProfile {
    demoProfile = { ...demoProfile, ...patch };
    return { ...demoProfile };
  },

  getFarms(): Farm[] {
    return [...demoFarms];
  },

  createFarm(payload: Omit<Farm, 'id' | 'user_id' | 'created_at' | 'updated_at'>): Farm {
    const created: Farm = {
      ...payload,
      id: makeId('farm'),
      user_id: 'demo-farmer-001',
      created_at: new Date().toISOString(),
    };
    demoFarms = [created, ...demoFarms];
    return created;
  },

  updateFarm(
    id: string,
    patch: Partial<Omit<Farm, 'id' | 'user_id' | 'created_at' | 'updated_at'>>
  ): Farm {
    let updatedFarm: Farm | undefined;
    demoFarms = demoFarms.map((f) => {
      if (f.id !== id) return f;
      updatedFarm = { ...f, ...patch };
      return updatedFarm;
    });
    if (!updatedFarm) {
      throw new Error('Farm plot not found.');
    }
    return { ...updatedFarm };
  },

  deleteFarm(id: string): void {
    demoFarms = demoFarms.filter((f) => f.id !== id);
  },

  predictYield(req: CropYieldRequest): CropYieldResponse {
    const isCoconut = req.crop.trim().toLowerCase() === 'coconut';
    const fertPerHa = req.fertilizer_kg / Math.max(req.area_hectares, 0.1);
    const rainFactor = Math.min(1.25, Math.max(0.75, req.annual_rainfall_mm / 1250));
    const fertFactor = Math.min(1.3, Math.max(0.85, 0.9 + Math.log10(fertPerHa + 10) * 0.12));

    const cropBaselines: Record<string, number> = {
      Coconut: 8650,
      Sugarcane: 52.4,
      Banana: 27.1,
      Potato: 13.8,
      Onion: 13.1,
      Rice: 3.45,
      Wheat: 3.12,
      Maize: 2.95,
      'Cotton(lint)': 1.75,
      Arecanut: 1.48,
    };

    const base = cropBaselines[req.crop] ?? 1.65;
    const predicted = Number((base * rainFactor * fertFactor).toFixed(2));
    const total = Number((predicted * req.area_hectares).toFixed(2));

    const predictedEntry: CropYieldResponse = {
      id: makeId('yield'),
      farm_id: req.farm_id ?? null,
      crop: req.crop,
      state: req.state,
      season: req.season,
      crop_year: req.crop_year,
      area_hectares: req.area_hectares,
      predicted_yield: predicted,
      yield_unit: isCoconut ? 'nuts/hectare' : 'tonnes/hectare',
      estimated_total_production: total,
      production_unit: isCoconut ? 'nuts' : 'tonnes',
      model_name: 'Phase 3 Preview Estimator (Demo Sandbox Only)',
      model_version: 'preview-v0',
      feature_drivers: [
        { feature: 'Crop Variety', impact_pct: 42, direction: 'positive' },
        { feature: 'Annual Rainfall (mm)', impact_pct: 26, direction: rainFactor >= 1 ? 'positive' : 'negative' },
        { feature: 'Fertilizer Intensity (kg/ha)', impact_pct: 19, direction: 'positive' },
        { feature: 'State Agro-Climatic Zone', impact_pct: 13, direction: 'neutral' },
      ],
      advisory_note:
        'Demo preview estimate generated locally in browser sandbox (no Production leakage). Sign in with a live backend account to run the trained Phase 5 Crop Yield ML pipeline.',
      created_at: new Date().toISOString(),
      source_mode: 'demo_preview',
    };
    demoYieldHistory = [predictedEntry, ...demoYieldHistory].slice(0, 10);
    return predictedEntry;
  },

  getYieldHistory(): CropYieldResponse[] {
    return [...demoYieldHistory];
  },

  detectDisease(file: File, cropHint: string): DiseaseDetectionResponse {
    const nameLower = file.name.toLowerCase();
    const isBlurryOrUnknown = nameLower.includes('unknown') || nameLower.includes('blur') || file.size < 18000;
    const isHealthy = nameLower.includes('healthy');

    let label = 'Tomato___Early_blight';
    let cropName = cropHint || 'Tomato';
    let diseaseName = 'Early Blight (Alternaria solani)';
    let confidence = 0.87;
    let isUncertain = false;

    if (isHealthy) {
      label = `${cropName}___Healthy`;
      diseaseName = 'Healthy Foliage';
      confidence = 0.93;
    } else if (nameLower.includes('rust')) {
      label = 'Corn___Common_rust';
      cropName = 'Maize / Corn';
      diseaseName = 'Common Rust (Puccinia sorghi)';
      confidence = 0.84;
    } else if (isBlurryOrUnknown) {
      label = `${cropName}___Leaf_spot_uncertain`;
      diseaseName = 'Unverified Foliar Stress / Spot';
      confidence = 0.54;
      isUncertain = true;
    }

    return {
      id: makeId('scan'),
      image_filename: file.name,
      predicted_label: label,
      crop_name: cropName,
      disease_name: diseaseName,
      is_healthy: isHealthy,
      confidence,
      is_uncertain: isUncertain,
      uncertainty_reason: isUncertain
        ? 'Confidence is below 65%. Leaf lighting, framing, or symptom overlap prevents reliable classification — capture a sharp close-up of a single leaf in daylight or consult a plant pathologist.'
        : null,
      top_predictions: [
        { label, confidence },
        { label: `${cropName}___Septoria_leaf_spot`, confidence: Number(((1 - confidence) * 0.65).toFixed(2)) },
        { label: `${cropName}___Healthy`, confidence: Number(((1 - confidence) * 0.35).toFixed(2)) },
      ],
      treatment_summary: isHealthy
        ? 'No pathology detected in preview check. Maintain routine scouting and balanced irrigation.'
        : 'Remove severely infected lower leaves, avoid overhead irrigation in late evening, and consult your local Krishi Vigyan Kendra (KVK) before applying crop-labeled protectant fungicides.',
      prevention_notes:
        'Ensure proper plant spacing for airflow, sanitize pruning tools, and follow 2–3 season crop rotation.',
      model_version: 'preview-v0 (PlantVillage CNN trained in Phase 7)',
      created_at: new Date().toISOString(),
      source_mode: 'demo_preview',
    };
  },

  recommendFertilizer(req: FertilizerRequest): FertilizerResponse {
    const lowN = req.nitrogen < 40;
    const lowP = req.phosphorus < 30;
    const lowK = req.potassium < 30;
    const allSufficient = !lowN && !lowP && !lowK;

    let mlGrade: string | null = '20-20';
    let recommended = '20-20';
    let mode: 'ml_grade_with_agronomic_guardrails' | 'agronomic_sufficiency_guardrail' =
      'ml_grade_with_agronomic_guardrails';
    let confidence = 0.89;

    if (allSufficient) {
      mlGrade = null;
      mode = 'agronomic_sufficiency_guardrail';
      recommended = 'Soil Nutrients Sufficient — Organic Maintenance Only';
      confidence = 1.0;
    } else if (lowN && !lowP && !lowK) {
      mlGrade = 'Urea';
      recommended = 'Urea';
    } else if (lowP && !lowN && !lowK) {
      mlGrade = 'DAP';
      recommended = 'DAP';
    } else if (lowP && lowN && lowK) {
      mlGrade = '17-17-17';
      recommended = '17-17-17';
    } else if (lowK && lowP) {
      mlGrade = '10-26-26';
      recommended = '10-26-26';
    } else if (lowP && req.phosphorus < 15) {
      mlGrade = '14-35-14';
      recommended = '14-35-14';
    } else if (lowN && lowP) {
      mlGrade = req.nitrogen < 20 ? '28-28' : '20-20';
      recommended = mlGrade;
    }

    const phAssessment =
      req.soil_ph < 5.8
        ? `Acidic soil (pH ${req.soil_ph.toFixed(1)} < 5.8): Consult a local KVK lab regarding soil-buffer-calibrated lime amendment before mineral NPK application.`
        : req.soil_ph > 7.8
          ? `Alkaline soil (pH ${req.soil_ph.toFixed(1)} > 7.8): Seek KVK confirmation for organic matter enrichment or gypsum/chelated micronutrient management.`
          : `Favorable soil reaction (pH ${req.soil_ph.toFixed(1)}, within 5.8–7.8): Primary macronutrient availability is well supported.`;

    const entry: FertilizerResponse = {
      id: makeId('fert'),
      farm_id: req.farm_id ?? null,
      nitrogen: req.nitrogen,
      phosphorus: req.phosphorus,
      potassium: req.potassium,
      soil_ph: req.soil_ph,
      soil_type: req.soil_type,
      crop_type: req.crop_type,
      location: req.location ?? null,
      recommended_fertilizer: recommended,
      confidence,
      ml_predicted_grade: mlGrade,
      recommendation_mode: mode,
      dataset_coverage_note: `Preview sandbox assessment mapping ${req.crop_type} and ${req.soil_type} texture against benchmark grade classes.`,
      nutrient_levels: [
        {
          nutrient: 'Nitrogen (N)',
          value: req.nitrogen,
          optimal_min: 40,
          optimal_max: 95,
          status: req.nitrogen < 40 ? 'low' : req.nitrogen > 95 ? 'high' : 'optimal',
        },
        {
          nutrient: 'Phosphorus (P)',
          value: req.phosphorus,
          optimal_min: 30,
          optimal_max: 65,
          status: req.phosphorus < 30 ? 'low' : req.phosphorus > 65 ? 'high' : 'optimal',
        },
        {
          nutrient: 'Potassium (K)',
          value: req.potassium,
          optimal_min: 30,
          optimal_max: 75,
          status: req.potassium < 30 ? 'low' : req.potassium > 75 ? 'high' : 'optimal',
        },
      ],
      ph_assessment: phAssessment,
      advisory_notes: allSufficient
        ? `Rule Guardrail Active (${req.crop_type} on ${req.soil_type}, ${req.location || 'Regional'}): Measured macronutrients meet sufficiency thresholds. Avoid unnecessary chemical inputs and maintain organic compost.`
        : `Preview ML Grade + Agronomic Balancing (${req.crop_type} on ${req.soil_type}, ${req.location || 'Regional'}): Use split timing across basal and vegetative stages and confirm exact field rates with KVK testing.`,
      expert_disclaimer:
        'Qualitative formulation guidance only — chemical application rates (kg/ha or g/plant) are intentionally NOT fabricated. Confirm exact field doses via accredited Soil Health Card testing and your local KVK.',
      model_version: 'preview-v0',
      created_at: new Date().toISOString(),
      source_mode: 'demo_preview',
    };
    demoFertilizerHistory = [entry, ...demoFertilizerHistory].slice(0, 10);
    return entry;
  },

  getFertilizerHistory(): FertilizerResponse[] {
    return [...demoFertilizerHistory];
  },

  recommendCrop(req: CropRecommendationRequest): CropRecommendationResponse {
    let primary = 'rice';
    let secondary = 'jute';
    let tertiary = 'maize';

    if (req.rainfall_mm < 70 && req.temperature_c > 26) {
      primary = 'mothbeans';
      secondary = 'watermelon';
      tertiary = 'chickpea';
    } else if (req.soil_ph >= 6.0 && req.soil_ph <= 7.2 && req.potassium > 60) {
      primary = 'banana';
      secondary = 'grapes';
      tertiary = 'papaya';
    } else if (req.temperature_c < 20) {
      primary = 'apple';
      secondary = 'lentil';
      tertiary = 'kidneybeans';
    } else if (req.rainfall_mm > 170 && req.humidity_pct > 75) {
      primary = 'rice';
      secondary = 'coconut';
      tertiary = 'jute';
    } else if (req.nitrogen > 80 && req.humidity_pct < 75) {
      primary = 'cotton';
      secondary = 'maize';
      tertiary = 'coffee';
    }

    const entry: CropRecommendationResponse = {
      id: makeId('crop'),
      farm_id: req.farm_id ?? null,
      nitrogen: req.nitrogen,
      phosphorus: req.phosphorus,
      potassium: req.potassium,
      temperature_c: req.temperature_c,
      humidity_pct: req.humidity_pct,
      soil_ph: req.soil_ph,
      rainfall_mm: req.rainfall_mm,
      season: req.season ?? null,
      region: req.region ?? null,
      recommended_crop: primary,
      top_candidates: [
        {
          crop: primary,
          probability: 0.78,
          fit_reason: `Strong match for pH ${req.soil_ph.toFixed(1)}, ${req.rainfall_mm} mm rainfall, and ${req.temperature_c}°C ambient profile.`,
        },
        {
          crop: secondary,
          probability: 0.15,
          fit_reason: `Viable secondary candidate across NPK (${req.nitrogen}-${req.phosphorus}-${req.potassium}) and climate envelope.`,
        },
        {
          crop: tertiary,
          probability: 0.07,
          fit_reason: 'Moderate rotational diversification candidate.',
        },
      ],
      soil_climate_summary: `Evaluated soil NPK (${req.nitrogen}-${req.phosphorus}-${req.potassium}), pH ${req.soil_ph.toFixed(1)}, ${req.temperature_c.toFixed(1)}°C, ${req.humidity_pct}% humidity, and ${req.rainfall_mm} mm rainfall. Preview mode approximates the 7-feature model.`,
      model_version: 'preview-v0',
      created_at: new Date().toISOString(),
      source_mode: 'demo_preview',
    };
    demoCropRecHistory = [entry, ...demoCropRecHistory].slice(0, 10);
    return entry;
  },

  getCropRecHistory(): CropRecommendationResponse[] {
    return [...demoCropRecHistory];
  },

  getWeatherIrrigation(req: WeatherIrrigationRequest): WeatherIrrigationResponse {
    const forecast = Array.from({ length: 7 }).map((_, idx) => {
      const d = new Date(Date.now() + idx * 86400000);
      const rain = idx === 2 ? 14.2 : idx === 3 ? 8.6 : idx === 5 ? 3.4 : 0.4;
      const tempMax = Number((30.5 - (idx % 3) * 1.1).toFixed(1));
      const et0 = Number((4.4 - rain * 0.08).toFixed(2));
      return {
        date: d.toISOString().slice(0, 10),
        temp_max_c: tempMax,
        temp_min_c: Number((tempMax - 7.8).toFixed(1)),
        humidity_pct: Math.min(92, Math.round(64 + rain * 1.5)),
        rain_mm: rain,
        et0_mm: Math.max(2.1, et0),
      };
    });

    const totalRain = Number(forecast.reduce((s, p) => s + p.rain_mm, 0).toFixed(1));
    const avgEt0 = Number((forecast.reduce((s, p) => s + p.et0_mm, 0) / 7).toFixed(2));
    const kcMap: Record<string, number> = {
      initial: 0.55,
      development: 0.85,
      mid_season: 1.15,
      late_season: 0.75,
    };
    const kc = kcMap[req.growth_stage] ?? 1.0;
    const netNeed = Math.max(0, Number((avgEt0 * 7 * kc - totalRain * 0.75).toFixed(1)));

    return {
      id: makeId('irr'),
      location_name: req.location_name,
      latitude: req.latitude,
      longitude: req.longitude,
      crop_type: req.crop_type,
      growth_stage: req.growth_stage,
      weather_provider: 'Open-Meteo Preview Stub (Live API wired in Phase 7)',
      current_temp_c: 29.8,
      current_humidity_pct: 68,
      wind_speed_kmh: 11.4,
      weather_condition: 'Partly Cloudy — Light Monsoon Moisture',
      forecast_rainfall_7d_mm: totalRain,
      estimated_et0_mm: avgEt0,
      recommended_water_mm: netNeed,
      irrigation_urgency: netNeed < 5 ? 'skip_rain_expected' : netNeed < 18 ? 'moderate' : 'high',
      is_sensor_backed: false,
      sensor_notice:
        'Weather-Estimated Advisory Only: Calculations use meteorological ET₀ and forecast precipitation, NOT physical in-field soil moisture probe readings.',
      advisory_notes: `Estimated 7-day crop water deficit for ${req.crop_type} (${req.growth_stage.replace('_', ' ')}): ${netNeed} mm after accounting for expected ${totalRain} mm forecast rain.`,
      alerts: [
        {
          severity: 'info',
          title: 'Mid-Week Rain Window Expected',
          message: 'Forecast indicates ~22.8 mm cumulative showers between Day 3 and Day 4. Defer heavy flood irrigation.',
        },
      ],
      forecast_7d: forecast,
      created_at: new Date().toISOString(),
      source_mode: 'demo_preview',
    };
  },

  getChatSessions(): ChatSession[] {
    return [...demoSessions];
  },

  createChatSession(language: SupportedLanguage, title?: string): ChatSession {
    const s: ChatSession = {
      id: makeId('chat'),
      title: title || `Consultation (${language.toUpperCase()})`,
      language,
      farm_id: demoFarms[0]?.id ?? null,
      updated_at: new Date().toISOString(),
    };
    demoSessions = [s, ...demoSessions];
    demoMessages[s.id] = [];
    return s;
  },

  getChatMessages(sessionId: string): ChatMessage[] {
    return [...(demoMessages[sessionId] || [])];
  },

  clearChatMessages(sessionId: string): void {
    demoMessages[sessionId] = [];
  },

  sendChatMessage(
    sessionId: string,
    prompt: string,
    language: SupportedLanguage
  ): { userMsg: ChatMessage; assistantMsg: ChatMessage } {
    const userMsg: ChatMessage = {
      id: makeId('msg'),
      session_id: sessionId,
      role: 'user',
      content: prompt,
      citations: [],
      provider: null,
      model_name: null,
      created_at: new Date().toISOString(),
    };

    const langGreetings: Record<SupportedLanguage, string> = {
      en: '[Preview Mode — Live Gemini RAG connects in Phase 6]\n\nBased on TerraQora agronomy baselines:',
      ta: '[முன்னோட்ட முறை — Phase 6-இல் நேரடி Gemini AI இணைக்கப்படும்]\n\nஉங்கள் கேள்விக்கான பொதுவான வேளாண் ஆலோசனை:',
      ml: '[പ്രിവ്യൂ മോഡ് — Phase 6-ൽ തത്സമയ Gemini AI ബന്ധിപ്പിക്കും]\n\nനിങ്ങളുടെ ചോദ്യത്തിനുള്ള പ്രാഥമിക കാർഷിക നിർദ്ദേശം:',
      hi: '[प्रीव्यू मोड — Phase 6 में लाइव Gemini AI जोड़ा जाएगा]\n\nआपके प्रश्न के लिए प्रारंभिक कृषि मार्गदर्शन:',
      te: '[ప్రివ్యూ మోడ్ — Phase 6లో లైవ్ Gemini AI కనెక్ట్ అవుతుంది]\n\nమీ ప్రశ్నకు ప్రాథమిక వ్యవసాయ సూచన:',
    };

    const assistantMsg: ChatMessage = {
      id: makeId('msg'),
      session_id: sessionId,
      role: 'assistant',
      content: `${langGreetings[language]} Regarding "${prompt.slice(0, 120)}":\n\n• Inspect soil moisture and drainage before scheduling fertilizer or irrigation operations.\n• Avoid applying unverified chemical dosages — always verify label rates and consult your district Krishi Vigyan Kendra (KVK) agronomist.\n• Use TerraQora's Crop Yield and Weather modules together to benchmark seasonal risk.`,
      citations: [
        { source_title: 'ICAR Nutrient & Irrigation Safety Guidelines', section: 'General Field Advisory' },
      ],
      provider: 'preview_sandbox',
      model_name: 'gemini-2.5-flash (preview)',
      created_at: new Date().toISOString(),
    };

    demoMessages[sessionId] = [...(demoMessages[sessionId] || []), userMsg, assistantMsg];
    demoSessions = demoSessions.map((s) =>
      s.id === sessionId ? { ...s, language, updated_at: new Date().toISOString() } : s
    );
    return { userMsg, assistantMsg };
  },

  getAnalytics(filters: AnalyticsFilter): AnalyticsResponse {
    // Grounded baseline derived from crop_yield.csv audit metrics (19,689 rows, 1997-2020)
    const stateScale = filters.state ? 0.14 : 1;
    const cropScale = filters.crop ? 0.18 : 1;
    const factor = Number((stateScale * cropScale).toFixed(2));
    const totalRecords = Math.max(18, Math.round(19689 * factor));

    const cropDist = [
      { name: 'Rice', records: Math.round(1197 * stateScale), avg_yield: 2.38 },
      { name: 'Maize', records: Math.round(975 * stateScale), avg_yield: 3.43 },
      { name: 'Moong(Green Gram)', records: Math.round(740 * stateScale), avg_yield: 0.62 },
      { name: 'Urad', records: Math.round(733 * stateScale), avg_yield: 0.69 },
      { name: 'Groundnut', records: Math.round(725 * stateScale), avg_yield: 1.54 },
      { name: 'Sesamum', records: Math.round(685 * stateScale), avg_yield: 0.61 },
      { name: 'Potato', records: Math.round(628 * stateScale), avg_yield: 13.33 },
      { name: 'Sugarcane', records: Math.round(605 * stateScale), avg_yield: 51.73 },
    ].filter((d) => !filters.crop || d.name === filters.crop);

    const stateProd = [
      { state: 'Karnataka', production_mt: 14.8, records: 1432 },
      { state: 'Andhra Pradesh', production_mt: 13.6, records: 1266 },
      { state: 'West Bengal', production_mt: 12.1, records: 1094 },
      { state: 'Uttar Pradesh', production_mt: 18.4, records: 825 },
      { state: 'Maharashtra', production_mt: 15.2, records: 760 },
      { state: 'Tamil Nadu', production_mt: 11.4, records: 822 },
      { state: 'Bihar', production_mt: 7.9, records: 896 },
    ].filter((s) => !filters.state || s.state === filters.state);

    const years = [2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020].filter(
      (y) =>
        (!filters.year_start || y >= filters.year_start) &&
        (!filters.year_end || y <= filters.year_end)
    );

    const annualTrends = years.map((y, i) => ({
      year: y,
      avg_rainfall: [1498, 1342, 1356, 1501, 1492, 1631, 1521, 1314][i % 8],
      avg_yield: Number((2.4 + i * 0.14).toFixed(2)),
      fertilizer_index: Math.round(21.2 + i * 0.8),
      pesticide_index: Math.round(44 + i * 2.1),
    }));

    return {
      total_records: totalRecords,
      unique_crops: filters.crop ? 1 : 55,
      unique_states: filters.state ? 1 : 30,
      avg_yield: filters.crop === 'Coconut' ? 8652.0 : 4.28,
      avg_rainfall_mm: 1437.8,
      total_fertilizer_tonnes: Math.round(474500 * factor),
      total_pesticide_tonnes: Math.round(961 * factor),
      crop_distribution: cropDist.length ? cropDist : [{ name: filters.crop || 'Rice', records: totalRecords, avg_yield: 2.9 }],
      state_production: stateProd.length ? stateProd : [{ state: filters.state || 'India', production_mt: 8.4, records: totalRecords }],
      annual_trends: annualTrends,
      yield_comparison: [
        { crop: 'Rice', kharif: 2.45, rabi: 2.82, whole_year: 2.31 },
        { crop: 'Maize', kharif: 2.68, rabi: 4.12, whole_year: 3.15 },
        { crop: 'Sugarcane', kharif: 48.2, rabi: 51.0, whole_year: 54.6 },
        { crop: 'Potato', kharif: 10.4, rabi: 14.8, whole_year: 12.1 },
      ],
      correlation_matrix: [
        { feature_x: 'Area', feature_y: 'Fertilizer', correlation: 0.97 },
        { feature_x: 'Area', feature_y: 'Pesticide', correlation: 0.96 },
        { feature_x: 'Fertilizer', feature_y: 'Pesticide', correlation: 0.98 },
        { feature_x: 'Rainfall', feature_y: 'Yield', correlation: 0.04 },
        { feature_x: 'Crop_Year', feature_y: 'Yield', correlation: 0.03 },
      ],
      source_mode: 'demo_preview',
    };
  },

  getReports(): GeneratedReport[] {
    return [...demoReports];
  },

  createReport(req: ReportCreateRequest): GeneratedReport {
    const rep: GeneratedReport = {
      id: makeId('rep'),
      title: req.title,
      crop: req.crop,
      state: req.state,
      season: req.season,
      area_hectares: req.area_hectares,
      predicted_yield: req.predicted_yield,
      yield_unit: req.yield_unit,
      model_explanation:
        'Leak-free feature evaluation considers agro-climatic state baseline, season, area, rainfall, and per-hectare nutrient inputs without post-harvest production leakage.',
      agricultural_observations: [
        `Target cultivation area: ${req.area_hectares} ha (${req.crop} in ${req.state}, ${req.season} season).`,
        `Estimated productivity: ${req.predicted_yield} ${req.yield_unit}.`,
        'Validate field moisture manually prior to altering irrigation cycles.',
      ],
      fertilizer_recommendation: req.fertilizer_recommendation,
      irrigation_summary: req.irrigation_summary,
      ai_summary: `Preview Executive Summary (${req.language.toUpperCase()}): Integrated assessment for ${req.crop} in ${req.state}. Combine split nutrient scheduling (${req.fertilizer_recommendation}) with forecast-adjusted irrigation (${req.irrigation_summary}). Consult a local agronomist before major input adjustments.`,
      pdf_filename: `TerraQora_${req.crop.replace(/\W+/g, '_')}_${req.state.replace(/\W+/g, '_')}.pdf`,
      created_at: new Date().toISOString(),
      source_mode: 'demo_preview',
    };
    demoReports = [rep, ...demoReports];
    return rep;
  },

  getAdminOverview(): AdminOverviewResponse {
    return {
      total_users: 42,
      active_farms: 68,
      total_predictions: 318,
      total_disease_scans: 129,
      total_ai_chats: 245,
      models: [
        {
          module: 'Crop Yield Prediction',
          algorithm: 'Segmented Histogram GBDT / RF (55 Crops, Leak-Free)',
          status: 'Active (Phase 5 Live · Demo Preview)',
          metric_label: 'Chronological Held-Out R²',
          metric_value: '0.838 (Non-Coco) / 0.873 (Coco)',
          artifact_size: '0.47 MB',
        },
        {
          module: 'Plant Disease Vision',
          algorithm: 'MobileNetV2 Transfer Learning (TensorFlow/Keras + TFLite)',
          status: 'Phase 7 Scheduled',
          metric_label: 'Validation F1',
          metric_value: 'Pending Phase 7 Training',
          artifact_size: '< 10 MB target',
        },
        {
          module: 'Crop Recommendation',
          algorithm: 'Gaussian Naive Bayes (7 Features, 22 Crops)',
          status: 'Active (Phase 5b Live · Demo Preview)',
          metric_label: 'Stratified Held-Out Test',
          metric_value: 'Acc 0.9955 | Macro-F1 0.9954',
          artifact_size: '5.6 KB',
        },
        {
          module: 'Fertilizer Recommendation',
          algorithm: 'Logistic Regression (NPK Grade) + ICAR Agronomic Guardrails',
          status: 'Active (Phase 5b Live · Demo Preview)',
          metric_label: 'Stratified Held-Out Test',
          metric_value: 'Macro-F1 1.0000 | 7 Grades',
          artifact_size: '1.6 KB',
        },
      ],
      users: [
        {
          id: 'demo-farmer-001',
          full_name: 'Ananya Sundaram',
          email: 'ananya.farmer@terraqora.demo',
          role: 'farmer',
          preferred_language: 'ta',
          is_active: true,
          farms_count: 2,
          predictions_count: 14,
          created_at: '2026-09-12T08:00:00Z',
        },
        {
          id: 'demo-farmer-002',
          full_name: 'Raghavendra Rao',
          email: 'raghav.agri@terraqora.demo',
          role: 'farmer',
          preferred_language: 'te',
          is_active: true,
          farms_count: 3,
          predictions_count: 21,
          created_at: '2026-10-02T11:30:00Z',
        },
        {
          id: 'demo-admin-001',
          full_name: 'Dr. Karthik Menon',
          email: 'admin@terraqora.demo',
          role: 'admin',
          preferred_language: 'en',
          is_active: true,
          farms_count: 1,
          predictions_count: 6,
          created_at: '2026-08-01T08:00:00Z',
        },
      ],
      source_mode: 'demo_preview',
    };
  },
};
