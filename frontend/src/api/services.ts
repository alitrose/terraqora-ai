import { ApiError, apiRequest, getApiMode, isDemoPreviewToken } from './client';
import { demoSandbox } from './demoSandbox';
import type {
  AdminOverviewResponse,
  AnalyticsFilter,
  AnalyticsResponse,
  AuthSession,
  ChatLanguageChoice,
  ChatMessage,
  ChatSession,
  ChatTurnResult,
  CropRecommendationRequest,
  CropRecommendationResponse,
  CropYieldRequest,
  CropYieldResponse,
  DiseaseDetectionResponse,
  Farm,
  FarmPayload,
  FarmUpdatePayload,
  FarmerProfile,
  FertilizerRequest,
  FertilizerResponse,
  GeneratedReport,
  LoginPayload,
  RegisterPayload,
  ReportCreateRequest,
  SupportedLanguage,
  User,
  UserOperationalAnalyticsResponse,
  WeatherIrrigationRequest,
  WeatherIrrigationResponse,
} from '../types/api';

async function withFallback<T>(
  liveCall: () => Promise<T>,
  fallbackCall: () => T,
  respectDemoToken = true
): Promise<T> {
  if (respectDemoToken && isDemoPreviewToken() && getApiMode() === 'auto') {
    return fallbackCall();
  }
  try {
    return await liveCall();
  } catch (err) {
    if (err instanceof ApiError && err.status === 0 && getApiMode() === 'auto') {
      return fallbackCall();
    }
    throw err;
  }
}

async function withPhasePendingFallback<T>(
  liveCall: () => Promise<T>,
  fallbackCall: () => T
): Promise<T> {
  if (isDemoPreviewToken() && getApiMode() === 'auto') {
    return fallbackCall();
  }
  try {
    return await liveCall();
  } catch (err) {
    if (
      err instanceof ApiError &&
      (err.status === 0 || err.status === 404 || err.status === 501) &&
      getApiMode() === 'auto'
    ) {
      return fallbackCall();
    }
    throw err;
  }
}

export const authService = {
  login: (payload: LoginPayload, demoRoleHint?: 'farmer' | 'admin') =>
    withFallback<AuthSession>(
      () =>
        apiRequest<AuthSession>('/auth/login', {
          method: 'POST',
          body: JSON.stringify(payload),
        }),
      () => demoSandbox.login(payload.email, demoRoleHint),
      false
    ),

  register: (payload: RegisterPayload) =>
    withFallback<AuthSession>(
      () =>
        apiRequest<AuthSession>('/auth/register', {
          method: 'POST',
          body: JSON.stringify(payload),
        }),
      () =>
        demoSandbox.register(
          payload.full_name,
          payload.email,
          payload.preferred_language
        ),
      false
    ),

  getMe: () =>
    withFallback<User>(
      () => apiRequest<User>('/auth/me'),
      () => demoSandbox.login('ananya.farmer@terraqora.demo').user
    ),
};

export const profileService = {
  getProfile: () =>
    withFallback<FarmerProfile>(
      () => apiRequest<FarmerProfile>('/profile'),
      () => demoSandbox.getProfile()
    ),

  updateProfile: (patch: Partial<FarmerProfile>) =>
    withFallback<FarmerProfile>(
      () =>
        apiRequest<FarmerProfile>('/profile', {
          method: 'PUT',
          body: JSON.stringify(patch),
        }),
      () => demoSandbox.updateProfile(patch)
    ),

  listFarms: () =>
    withFallback<Farm[]>(
      () => apiRequest<Farm[]>('/farms'),
      () => demoSandbox.getFarms()
    ),

  createFarm: (payload: FarmPayload) =>
    withFallback<Farm>(
      () =>
        apiRequest<Farm>('/farms', {
          method: 'POST',
          body: JSON.stringify(payload),
        }),
      () => demoSandbox.createFarm(payload)
    ),

  updateFarm: (id: string, patch: FarmUpdatePayload) =>
    withFallback<Farm>(
      () =>
        apiRequest<Farm>(`/farms/${id}`, {
          method: 'PUT',
          body: JSON.stringify(patch),
        }),
      () => demoSandbox.updateFarm(id, patch)
    ),

  deleteFarm: (id: string) =>
    withFallback<void>(
      () => apiRequest<void>(`/farms/${id}`, { method: 'DELETE' }),
      () => demoSandbox.deleteFarm(id)
    ),
};

export const mlService = {
  predictYield: (payload: CropYieldRequest) =>
    withFallback<CropYieldResponse>(
      () =>
        apiRequest<CropYieldResponse>('/predictions/yield', {
          method: 'POST',
          body: JSON.stringify(payload),
          timeoutMs: 12000,
        }),
      () => demoSandbox.predictYield(payload)
    ),

  getYieldHistory: () =>
    withFallback<CropYieldResponse[]>(
      () => apiRequest<CropYieldResponse[]>('/predictions/yield/history?limit=10'),
      () => demoSandbox.getYieldHistory()
    ),

  detectDisease: (file: File, cropHint: string, farmId?: string | null) =>
    withFallback<DiseaseDetectionResponse>(
      () => {
        const form = new FormData();
        form.append('file', file);
        if (cropHint.trim()) {
          form.append('crop_hint', cropHint.trim());
        }
        if (farmId) {
          form.append('farm_id', farmId);
        }
        return apiRequest<DiseaseDetectionResponse>('/disease/detect', {
          method: 'POST',
          body: form,
          timeoutMs: 25000,
        });
      },
      () => demoSandbox.detectDisease(file, cropHint, farmId)
    ),

  getDiseaseHistory: () =>
    withFallback<DiseaseDetectionResponse[]>(
      () => apiRequest<DiseaseDetectionResponse[]>('/disease/history?limit=10'),
      () => demoSandbox.getDiseaseHistory()
    ),

  recommendFertilizer: (payload: FertilizerRequest) =>
    withFallback<FertilizerResponse>(
      () =>
        apiRequest<FertilizerResponse>('/recommendations/fertilizer', {
          method: 'POST',
          body: JSON.stringify(payload),
          timeoutMs: 12000,
        }),
      () => demoSandbox.recommendFertilizer(payload)
    ),

  getFertilizerHistory: () =>
    withFallback<FertilizerResponse[]>(
      () => apiRequest<FertilizerResponse[]>('/recommendations/fertilizer/history?limit=10'),
      () => demoSandbox.getFertilizerHistory()
    ),

  recommendCrop: (payload: CropRecommendationRequest) =>
    withFallback<CropRecommendationResponse>(
      () =>
        apiRequest<CropRecommendationResponse>('/recommendations/crop', {
          method: 'POST',
          body: JSON.stringify(payload),
          timeoutMs: 12000,
        }),
      () => demoSandbox.recommendCrop(payload)
    ),

  getCropRecHistory: () =>
    withFallback<CropRecommendationResponse[]>(
      () => apiRequest<CropRecommendationResponse[]>('/recommendations/crop/history?limit=10'),
      () => demoSandbox.getCropRecHistory()
    ),
};

export const weatherService = {
  getIrrigationAdvisory: (payload: WeatherIrrigationRequest) =>
    withFallback<WeatherIrrigationResponse>(
      () =>
        apiRequest<WeatherIrrigationResponse>('/weather/irrigation', {
          method: 'POST',
          body: JSON.stringify(payload),
          timeoutMs: 14000,
        }),
      () => demoSandbox.getWeatherIrrigation(payload)
    ),

  getIrrigationHistory: () =>
    withFallback<WeatherIrrigationResponse[]>(
      () => apiRequest<WeatherIrrigationResponse[]>('/weather/irrigation/history?limit=10'),
      () => demoSandbox.getWeatherHistory()
    ),
};

export const chatService = {
  listSessions: () =>
    withFallback<ChatSession[]>(
      () => apiRequest<ChatSession[]>('/chat/sessions'),
      () => demoSandbox.getChatSessions()
    ),

  createSession: (
    language: SupportedLanguage,
    title?: string,
    farmId?: string | null
  ) =>
    withFallback<ChatSession>(
      () =>
        apiRequest<ChatSession>('/chat/sessions', {
          method: 'POST',
          body: JSON.stringify({
            language,
            ...(title ? { title } : {}),
            ...(farmId !== undefined ? { farm_id: farmId } : {}),
          }),
        }),
      () => demoSandbox.createChatSession(language, title, farmId)
    ),

  updateSession: (
    sessionId: string,
    patch: { title?: string; language?: SupportedLanguage; farm_id?: string | null }
  ) =>
    withFallback<ChatSession>(
      () =>
        apiRequest<ChatSession>(`/chat/sessions/${sessionId}`, {
          method: 'PATCH',
          body: JSON.stringify(patch),
        }),
      () => demoSandbox.updateChatSession(sessionId, patch)
    ),

  deleteSession: (sessionId: string) =>
    withFallback<void>(
      () =>
        apiRequest<void>(`/chat/sessions/${sessionId}`, {
          method: 'DELETE',
        }),
      () => demoSandbox.deleteChatSession(sessionId)
    ),

  getMessages: (sessionId: string) =>
    withFallback<ChatMessage[]>(
      () => apiRequest<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`),
      () => demoSandbox.getChatMessages(sessionId)
    ),

  clearSession: (sessionId: string) =>
    withFallback<void>(
      () =>
        apiRequest<void>(`/chat/sessions/${sessionId}/messages`, {
          method: 'DELETE',
        }),
      () => demoSandbox.clearChatMessages(sessionId)
    ),

  sendMessage: (
    sessionId: string,
    content: string,
    language: ChatLanguageChoice,
    includeFarmContext = true
  ) =>
    withFallback<ChatTurnResult>(
      async () => {
        const res = await apiRequest<{
          session: ChatSession;
          user_message: ChatMessage;
          assistant_message: ChatMessage;
          resolved_language: SupportedLanguage;
          language_auto_detected: boolean;
        }>(`/chat/sessions/${sessionId}/messages`, {
          method: 'POST',
          body: JSON.stringify({
            content,
            language,
            include_farm_context: includeFarmContext,
          }),
          timeoutMs: 30000,
        });
        return {
          session: res.session,
          userMsg: res.user_message,
          assistantMsg: res.assistant_message,
          resolvedLanguage: res.resolved_language,
          autoDetected: res.language_auto_detected,
        };
      },
      () => demoSandbox.sendChatMessage(sessionId, content, language)
    ),
};

export const analyticsService = {
  getOperational: (rangeDays: number = 30, farmId?: string) =>
    withFallback<UserOperationalAnalyticsResponse>(
      () => {
        const params = new URLSearchParams();
        params.set('range_days', String(rangeDays));
        if (farmId) params.set('farm_id', farmId);
        return apiRequest<UserOperationalAnalyticsResponse>(
          `/analytics/operational?${params.toString()}`
        );
      },
      () => demoSandbox.getOperationalAnalytics(rangeDays, farmId)
    ),

  getSummary: (filters: AnalyticsFilter) => {
    const params = new URLSearchParams();
    if (filters.crop) params.set('crop', filters.crop);
    if (filters.state) params.set('state', filters.state);
    if (filters.season) params.set('season', filters.season);
    if (filters.year_start) params.set('year_start', String(filters.year_start));
    if (filters.year_end) params.set('year_end', String(filters.year_end));
    const qs = params.toString();
    return withPhasePendingFallback<AnalyticsResponse>(
      () => apiRequest<AnalyticsResponse>(`/analytics/overview${qs ? `?${qs}` : ''}`),
      () => demoSandbox.getAnalytics(filters)
    );
  },
};

export const reportsService = {
  list: () =>
    withPhasePendingFallback<GeneratedReport[]>(
      () => apiRequest<GeneratedReport[]>('/reports'),
      () => demoSandbox.getReports()
    ),

  create: (payload: ReportCreateRequest) =>
    withPhasePendingFallback<GeneratedReport>(
      () =>
        apiRequest<GeneratedReport>('/reports', {
          method: 'POST',
          body: JSON.stringify(payload),
          timeoutMs: 25000,
        }),
      () => demoSandbox.createReport(payload)
    ),
};

export const adminService = {
  getOverview: () =>
    withFallback<AdminOverviewResponse>(
      () => apiRequest<AdminOverviewResponse>('/admin/overview'),
      () => demoSandbox.getAdminOverview()
    ),
};
