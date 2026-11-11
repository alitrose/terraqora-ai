import { ApiError, apiRequest, getApiMode } from './client';
import { demoSandbox } from './demoSandbox';
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
  LoginPayload,
  RegisterPayload,
  ReportCreateRequest,
  SupportedLanguage,
  User,
  WeatherIrrigationRequest,
  WeatherIrrigationResponse,
} from '../types/api';

async function withFallback<T>(
  liveCall: () => Promise<T>,
  fallbackCall: () => T
): Promise<T> {
  try {
    return await liveCall();
  } catch (err) {
    if (err instanceof ApiError && err.status === 0 && getApiMode() === 'auto') {
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
      () => demoSandbox.login(payload.email, demoRoleHint)
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
        )
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

  createFarm: (payload: Omit<Farm, 'id' | 'user_id' | 'created_at'>) =>
    withFallback<Farm>(
      () =>
        apiRequest<Farm>('/farms', {
          method: 'POST',
          body: JSON.stringify(payload),
        }),
      () => demoSandbox.createFarm(payload)
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

  detectDisease: (file: File, cropHint: string) =>
    withFallback<DiseaseDetectionResponse>(
      () => {
        const form = new FormData();
        form.append('file', file);
        form.append('crop_hint', cropHint);
        return apiRequest<DiseaseDetectionResponse>('/disease/detect', {
          method: 'POST',
          body: form,
          timeoutMs: 20000,
        });
      },
      () => demoSandbox.detectDisease(file, cropHint)
    ),

  recommendFertilizer: (payload: FertilizerRequest) =>
    withFallback<FertilizerResponse>(
      () =>
        apiRequest<FertilizerResponse>('/recommendations/fertilizer', {
          method: 'POST',
          body: JSON.stringify(payload),
        }),
      () => demoSandbox.recommendFertilizer(payload)
    ),

  recommendCrop: (payload: CropRecommendationRequest) =>
    withFallback<CropRecommendationResponse>(
      () =>
        apiRequest<CropRecommendationResponse>('/recommendations/crop', {
          method: 'POST',
          body: JSON.stringify(payload),
        }),
      () => demoSandbox.recommendCrop(payload)
    ),
};

export const weatherService = {
  getIrrigationAdvisory: (payload: WeatherIrrigationRequest) =>
    withFallback<WeatherIrrigationResponse>(
      () =>
        apiRequest<WeatherIrrigationResponse>('/weather/irrigation', {
          method: 'POST',
          body: JSON.stringify(payload),
          timeoutMs: 12000,
        }),
      () => demoSandbox.getWeatherIrrigation(payload)
    ),
};

export const chatService = {
  listSessions: () =>
    withFallback<ChatSession[]>(
      () => apiRequest<ChatSession[]>('/chat/sessions'),
      () => demoSandbox.getChatSessions()
    ),

  createSession: (language: SupportedLanguage, title?: string) =>
    withFallback<ChatSession>(
      () =>
        apiRequest<ChatSession>('/chat/sessions', {
          method: 'POST',
          body: JSON.stringify({ language, title }),
        }),
      () => demoSandbox.createChatSession(language, title)
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

  sendMessage: (sessionId: string, content: string, language: SupportedLanguage) =>
    withFallback<{ userMsg: ChatMessage; assistantMsg: ChatMessage }>(
      async () => {
        const res = await apiRequest<{
          user_message: ChatMessage;
          assistant_message: ChatMessage;
        }>(`/chat/sessions/${sessionId}/messages`, {
          method: 'POST',
          body: JSON.stringify({ content, language }),
          timeoutMs: 30000,
        });
        return { userMsg: res.user_message, assistantMsg: res.assistant_message };
      },
      () => demoSandbox.sendChatMessage(sessionId, content, language)
    ),
};

export const analyticsService = {
  getSummary: (filters: AnalyticsFilter) => {
    const params = new URLSearchParams();
    if (filters.crop) params.set('crop', filters.crop);
    if (filters.state) params.set('state', filters.state);
    if (filters.season) params.set('season', filters.season);
    if (filters.year_start) params.set('year_start', String(filters.year_start));
    if (filters.year_end) params.set('year_end', String(filters.year_end));
    const qs = params.toString();
    return withFallback<AnalyticsResponse>(
      () => apiRequest<AnalyticsResponse>(`/analytics/overview${qs ? `?${qs}` : ''}`),
      () => demoSandbox.getAnalytics(filters)
    );
  },
};

export const reportsService = {
  list: () =>
    withFallback<GeneratedReport[]>(
      () => apiRequest<GeneratedReport[]>('/reports'),
      () => demoSandbox.getReports()
    ),

  create: (payload: ReportCreateRequest) =>
    withFallback<GeneratedReport>(
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
