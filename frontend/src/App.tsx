import { BrowserRouter, Link, Route, Routes } from 'react-router-dom';
import { BrandLogo } from './components/BrandLogo';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { AdminDashboardPage } from './pages/AdminDashboardPage';
import { AgricultureAnalyticsPage } from './pages/AgricultureAnalyticsPage';
import { AIReportsPage } from './pages/AIReportsPage';
import { AuthPage } from './pages/AuthPage';
import { CropRecommendationPage } from './pages/CropRecommendationPage';
import { CropYieldPredictionPage } from './pages/CropYieldPredictionPage';
import { FarmerDashboardPage } from './pages/FarmerDashboardPage';
import { FertilizerRecommendationPage } from './pages/FertilizerRecommendationPage';
import { GenAIAssistantPage } from './pages/GenAIAssistantPage';
import { LandingPage } from './pages/LandingPage';
import { PlantDiseaseDetectionPage } from './pages/PlantDiseaseDetectionPage';
import { UserProfilePage } from './pages/UserProfilePage';
import { WeatherIrrigationPage } from './pages/WeatherIrrigationPage';

function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-parchment px-6 text-center text-soil-charcoal">
      <BrandLogo />
      <h1 className="mt-6 font-display text-3xl font-bold text-forest-deep">Page not found</h1>
      <p className="mt-2 max-w-md text-sm text-soil-muted">
        The requested TerraQora AI route does not exist. Return to the landing page or your
        farmer workspace.
      </p>
      <div className="mt-6 flex gap-3">
        <Link
          to="/"
          className="rounded-xl border border-soil-border bg-white px-4 py-2 text-sm font-semibold text-forest-deep hover:bg-parchment-muted"
        >
          Back Home
        </Link>
        <Link
          to="/dashboard"
          className="rounded-xl bg-forest-deep px-4 py-2 text-sm font-semibold text-white hover:bg-forest-hover"
        >
          Farmer Dashboard
        </Link>
      </div>
    </div>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/auth" element={<AuthPage />} />

      {/* Authenticated Farmer & Shared Routes */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <FarmerDashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/yield-prediction"
        element={
          <ProtectedRoute>
            <CropYieldPredictionPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/disease-detection"
        element={
          <ProtectedRoute>
            <PlantDiseaseDetectionPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/fertilizer"
        element={
          <ProtectedRoute>
            <FertilizerRecommendationPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/crop-recommendation"
        element={
          <ProtectedRoute>
            <CropRecommendationPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/weather-irrigation"
        element={
          <ProtectedRoute>
            <WeatherIrrigationPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/assistant"
        element={
          <ProtectedRoute>
            <GenAIAssistantPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/analytics"
        element={
          <ProtectedRoute>
            <AgricultureAnalyticsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports"
        element={
          <ProtectedRoute>
            <AIReportsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <UserProfilePage />
          </ProtectedRoute>
        }
      />

      {/* Admin-Only Route */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute requiredRole="admin">
            <AdminDashboardPage />
          </ProtectedRoute>
        }
      />

      {/* Fallback */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  );
}

export default App;
