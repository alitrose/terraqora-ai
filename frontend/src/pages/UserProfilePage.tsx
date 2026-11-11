import React, { useEffect, useState } from 'react';
import { MapPin, Pencil, Plus, Save, Trash2, UserCheck, X } from 'lucide-react';
import { profileService } from '../api/services';
import { AppShell } from '../components/AppShell';
import {
  EmptyState,
  ErrorAlert,
  LoadingSkeleton,
} from '../components/StatusState';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import {
  INDIAN_STATES,
  LANGUAGE_OPTIONS,
  SOIL_TYPES,
  YIELD_CROPS,
} from '../data/agriCatalog';
import type { Farm, FarmerProfile, SupportedLanguage } from '../types/api';

const IRRIGATION_OPTIONS: Array<NonNullable<Farm['irrigation_type']>> = [
  'drip',
  'canal',
  'borewell',
  'sprinkler',
  'rainfed',
  'mixed',
];

export function UserProfilePage() {
  const { user, updateUserLocal } = useAuth();
  const { notify } = useToast();

  const [profile, setProfile] = useState<FarmerProfile | null>(null);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingFarm, setSavingFarm] = useState(false);
  const [editingFarmId, setEditingFarmId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Profile form fields
  const [preferredLanguage, setPreferredLanguage] = useState<SupportedLanguage>(
    user?.preferred_language || 'en'
  );
  const [state, setState] = useState<string>('Tamil Nadu');
  const [district, setDistrict] = useState<string>('');
  const [phone, setPhone] = useState<string>('');
  const [experienceYears, setExperienceYears] = useState<number>(5);
  const [primarySoil, setPrimarySoil] = useState<string>(SOIL_TYPES[0]);
  const [preferredUnits, setPreferredUnits] = useState<'metric' | 'imperial'>('metric');

  // Add / Edit farm form fields
  const [farmName, setFarmName] = useState('');
  const [farmState, setFarmState] = useState<string>('Tamil Nadu');
  const [farmDistrict, setFarmDistrict] = useState('');
  const [farmArea, setFarmArea] = useState<number>(2.5);
  const [farmSoilType, setFarmSoilType] = useState<string>(SOIL_TYPES[0]);
  const [farmPh, setFarmPh] = useState<number>(6.5);
  const [farmIrrigation, setFarmIrrigation] =
    useState<NonNullable<Farm['irrigation_type']>>('drip');
  const [farmCrop, setFarmCrop] = useState<string>('Rice');

  const resetFarmForm = () => {
    setEditingFarmId(null);
    setFarmName('');
    setFarmState('Tamil Nadu');
    setFarmDistrict('');
    setFarmArea(2.5);
    setFarmSoilType(SOIL_TYPES[0]);
    setFarmPh(6.5);
    setFarmIrrigation('drip');
    setFarmCrop('Rice');
  };

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [prof, farmList] = await Promise.all([
        profileService.getProfile(),
        profileService.listFarms(),
      ]);
      setProfile(prof);
      setFarms(farmList);

      if (prof.preferred_language) {
        setPreferredLanguage(prof.preferred_language);
      } else if (user?.preferred_language) {
        setPreferredLanguage(user.preferred_language);
      }
      setState(prof.state || 'Tamil Nadu');
      setDistrict(prof.district || '');
      setPhone(prof.phone || '');
      setExperienceYears(prof.experience_years ?? 0);
      setPrimarySoil(prof.primary_soil_type || SOIL_TYPES[0]);
      setPreferredUnits(prof.preferred_units);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load profile data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (experienceYears < 0 || experienceYears > 90) {
      setError('Farming experience must be between 0 and 90 years.');
      return;
    }

    setSavingProfile(true);
    try {
      const updated = await profileService.updateProfile({
        state,
        district: district.trim() || null,
        phone: phone.trim() || null,
        experience_years: experienceYears,
        primary_soil_type: primarySoil,
        preferred_units: preferredUnits,
        preferred_language: preferredLanguage,
      });
      setProfile(updated);
      updateUserLocal({ preferred_language: preferredLanguage });
      notify('Farmer profile updated successfully', 'success');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update profile.');
    } finally {
      setSavingProfile(false);
    }
  };

  const handleStartEditFarm = (farm: Farm) => {
    setError(null);
    setEditingFarmId(farm.id);
    setFarmName(farm.name);
    setFarmState(farm.state);
    setFarmDistrict(farm.district || '');
    setFarmArea(farm.area_hectares);
    setFarmSoilType(farm.soil_type || SOIL_TYPES[0]);
    setFarmPh(farm.soil_ph ?? 6.5);
    setFarmIrrigation(farm.irrigation_type || 'drip');
    setFarmCrop(farm.primary_crop || 'Rice');
  };

  const handleSaveFarm = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (farmName.trim().length < 2) {
      setError('Farm plot name must be at least 2 characters.');
      return;
    }
    if (farmArea <= 0) {
      setError('Farm area must be greater than 0 hectares.');
      return;
    }
    if (farmPh < 0 || farmPh > 14) {
      setError('Farm soil pH must be between 0.0 and 14.0.');
      return;
    }

    const payload = {
      name: farmName.trim(),
      state: farmState,
      district: farmDistrict.trim() || null,
      latitude: null,
      longitude: null,
      area_hectares: farmArea,
      soil_type: farmSoilType,
      soil_ph: farmPh,
      irrigation_type: farmIrrigation,
      primary_crop: farmCrop,
    };

    setSavingFarm(true);
    try {
      if (editingFarmId) {
        const updated = await profileService.updateFarm(editingFarmId, payload);
        setFarms((prev) => prev.map((f) => (f.id === editingFarmId ? updated : f)));
        resetFarmForm();
        notify(`Updated farm "${updated.name}"`, 'success');
      } else {
        const created = await profileService.createFarm(payload);
        setFarms((prev) => [created, ...prev]);
        resetFarmForm();
        notify(`Registered farm "${created.name}"`, 'success');
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : editingFarmId
            ? 'Unable to update farm.'
            : 'Unable to register farm.'
      );
    } finally {
      setSavingFarm(false);
    }
  };

  const handleDeleteFarm = async (id: string, name: string) => {
    setError(null);
    try {
      await profileService.deleteFarm(id);
      setFarms((prev) => prev.filter((f) => f.id !== id));
      if (editingFarmId === id) {
        resetFarmForm();
      }
      notify(`Removed farm "${name}"`, 'info');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete farm.');
    }
  };

  return (
    <AppShell
      title="Farmer Profile & Registered Plots"
      subtitle="Manage your regional consultation preferences, default units, and farm plot metadata."
    >
      {error && (
        <div className="mb-6">
          <ErrorAlert message={error} onRetry={loading ? loadData : undefined} />
        </div>
      )}

      {loading ? (
        <div className="grid gap-6 lg:grid-cols-12">
          <div className="lg:col-span-5">
            <LoadingSkeleton rows={6} />
          </div>
          <div className="lg:col-span-7">
            <LoadingSkeleton rows={6} />
          </div>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-12">
          {/* Farmer Profile Form */}
          <form
            onSubmit={handleSaveProfile}
            className="space-y-4 rounded-2xl border border-soil-border bg-white p-6 shadow-card lg:col-span-5"
          >
            <div className="flex items-center gap-3 border-b border-soil-border pb-4">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-mist text-forest-deep">
                <UserCheck className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-display text-base font-bold text-forest-deep">
                  {user?.full_name || 'Farmer Account'}
                </h2>
                <p className="text-xs text-soil-muted">
                  {user?.email} · Role: <span className="uppercase font-semibold">{user?.role}</span>
                </p>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="prof-lang" className="block text-xs font-semibold text-soil-charcoal">
                  Preferred AI Language
                </label>
                <select
                  id="prof-lang"
                  value={preferredLanguage}
                  onChange={(e) => setPreferredLanguage(e.target.value as SupportedLanguage)}
                  className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
                >
                  {LANGUAGE_OPTIONS.map((opt) => (
                    <option key={opt.code} value={opt.code}>
                      {opt.label} ({opt.nativeLabel})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="prof-units" className="block text-xs font-semibold text-soil-charcoal">
                  Measurement Units
                </label>
                <select
                  id="prof-units"
                  value={preferredUnits}
                  onChange={(e) => setPreferredUnits(e.target.value as 'metric' | 'imperial')}
                  className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
                >
                  <option value="metric">Metric (Hectares / Tonnes / mm)</option>
                  <option value="imperial">Imperial (Acres / Tons / in)</option>
                </select>
              </div>

              <div>
                <label htmlFor="prof-state" className="block text-xs font-semibold text-soil-charcoal">
                  Primary State
                </label>
                <select
                  id="prof-state"
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                  className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
                >
                  {INDIAN_STATES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="prof-district" className="block text-xs font-semibold text-soil-charcoal">
                  District
                </label>
                <input
                  id="prof-district"
                  type="text"
                  value={district}
                  onChange={(e) => setDistrict(e.target.value)}
                  placeholder="e.g., Coimbatore"
                  className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label htmlFor="prof-phone" className="block text-xs font-semibold text-soil-charcoal">
                  Contact Phone
                </label>
                <input
                  id="prof-phone"
                  type="text"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+91 98400 00123"
                  className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label htmlFor="prof-exp" className="block text-xs font-semibold text-soil-charcoal">
                  Experience (Years)
                </label>
                <input
                  id="prof-exp"
                  type="number"
                  min={0}
                  max={90}
                  value={experienceYears}
                  onChange={(e) => setExperienceYears(Number(e.target.value))}
                  className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm"
                />
              </div>
            </div>

            <div>
              <label htmlFor="prof-soil" className="block text-xs font-semibold text-soil-charcoal">
                Primary Soil Texture
              </label>
              <select
                id="prof-soil"
                value={primarySoil}
                onChange={(e) => setPrimarySoil(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
              >
                {SOIL_TYPES.map((st) => (
                  <option key={st} value={st}>
                    {st}
                  </option>
                ))}
              </select>
            </div>

            {profile && (
              <p className="text-[11px] text-soil-muted">Profile ID: {profile.id}</p>
            )}

            <button
              type="submit"
              disabled={savingProfile}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-forest-deep py-2.5 text-sm font-semibold text-white hover:bg-forest-hover disabled:opacity-60"
            >
              <Save className="h-4 w-4 text-gold-bright" />
              {savingProfile ? 'Saving Changes...' : 'Save Profile Settings'}
            </button>
          </form>

          {/* Farms Management Column */}
          <div className="space-y-6 lg:col-span-7">
            {/* Add / Edit Farm Card */}
            <form
              onSubmit={handleSaveFarm}
              className="space-y-4 rounded-2xl border border-soil-border bg-white p-6 shadow-card"
            >
              <div className="flex items-center justify-between gap-2">
                <h2 className="font-display text-base font-bold text-forest-deep">
                  {editingFarmId ? 'Edit Farm Plot' : 'Register New Farm Plot'}
                </h2>
                {editingFarmId && (
                  <button
                    type="button"
                    onClick={resetFarmForm}
                    className="inline-flex items-center gap-1 rounded-lg border border-soil-border px-2.5 py-1 text-xs font-semibold text-soil-muted hover:bg-parchment hover:text-soil-charcoal"
                  >
                    <X className="h-3.5 w-3.5" />
                    Cancel Edit
                  </button>
                )}
              </div>

              <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
                <div className="sm:col-span-2 lg:col-span-1">
                  <label htmlFor="farm-name" className="block text-xs font-semibold text-soil-charcoal">
                    Plot / Farm Name
                  </label>
                  <input
                    id="farm-name"
                    type="text"
                    value={farmName}
                    onChange={(e) => setFarmName(e.target.value)}
                    placeholder="e.g., Erode East Block"
                    className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
                  />
                </div>

                <div>
                  <label htmlFor="farm-state" className="block text-xs font-semibold text-soil-charcoal">
                    State
                  </label>
                  <select
                    id="farm-state"
                    value={farmState}
                    onChange={(e) => setFarmState(e.target.value)}
                    className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
                  >
                    {INDIAN_STATES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="farm-district" className="block text-xs font-semibold text-soil-charcoal">
                    District
                  </label>
                  <input
                    id="farm-district"
                    type="text"
                    value={farmDistrict}
                    onChange={(e) => setFarmDistrict(e.target.value)}
                    placeholder="e.g., Erode"
                    className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
                  />
                </div>

                <div>
                  <label htmlFor="farm-area" className="block text-xs font-semibold text-soil-charcoal">
                    Area (ha)
                  </label>
                  <input
                    id="farm-area"
                    type="number"
                    min={0.1}
                    step={0.1}
                    value={farmArea}
                    onChange={(e) => setFarmArea(Number(e.target.value))}
                    className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm"
                  />
                </div>

                <div>
                  <label htmlFor="farm-soil" className="block text-xs font-semibold text-soil-charcoal">
                    Soil Type
                  </label>
                  <select
                    id="farm-soil"
                    value={farmSoilType}
                    onChange={(e) => setFarmSoilType(e.target.value)}
                    className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
                  >
                    {SOIL_TYPES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="farm-ph" className="block text-xs font-semibold text-soil-charcoal">
                    Soil pH
                  </label>
                  <input
                    id="farm-ph"
                    type="number"
                    min={0}
                    max={14}
                    step={0.1}
                    value={farmPh}
                    onChange={(e) => setFarmPh(Number(e.target.value))}
                    className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 font-mono text-sm"
                  />
                </div>

                <div>
                  <label htmlFor="farm-irr" className="block text-xs font-semibold text-soil-charcoal">
                    Irrigation Type
                  </label>
                  <select
                    id="farm-irr"
                    value={farmIrrigation}
                    onChange={(e) =>
                      setFarmIrrigation(e.target.value as NonNullable<Farm['irrigation_type']>)
                    }
                    className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm capitalize"
                  >
                    {IRRIGATION_OPTIONS.map((ir) => (
                      <option key={ir} value={ir}>
                        {ir}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="farm-crop" className="block text-xs font-semibold text-soil-charcoal">
                    Primary Crop
                  </label>
                  <select
                    id="farm-crop"
                    value={farmCrop}
                    onChange={(e) => setFarmCrop(e.target.value)}
                    className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2 text-sm"
                  >
                    {YIELD_CROPS.slice(0, 30).map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-end">
                  <button
                    type="submit"
                    disabled={savingFarm}
                    className="inline-flex w-full items-center justify-center gap-1.5 rounded-xl bg-emerald-leaf px-3 py-2.5 text-xs font-semibold text-white hover:bg-forest-hover disabled:opacity-60"
                  >
                    {editingFarmId ? (
                      <>
                        <Save className="h-4 w-4" />
                        {savingFarm ? 'Saving...' : 'Save Farm Changes'}
                      </>
                    ) : (
                      <>
                        <Plus className="h-4 w-4" />
                        {savingFarm ? 'Adding...' : 'Add Farm Plot'}
                      </>
                    )}
                  </button>
                </div>
              </div>
            </form>

            {/* Farm List */}
            <div className="rounded-2xl border border-soil-border bg-white p-6 shadow-card">
              <h2 className="font-display text-base font-bold text-forest-deep">
                Registered Farms ({farms.length})
              </h2>

              {farms.length === 0 ? (
                <div className="mt-4">
                  <EmptyState
                    title="No farm plots registered"
                    description="Use the form above to add a plot so reports and predictions auto-populate location context."
                  />
                </div>
              ) : (
                <div className="mt-4 space-y-3">
                  {farms.map((farm) => (
                    <div
                      key={farm.id}
                      className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-soil-border bg-parchment/60 p-4"
                    >
                      <div className="flex items-start gap-3">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-mist text-forest-deep">
                          <MapPin className="h-4 w-4" />
                        </div>
                        <div>
                          <p className="text-sm font-bold text-forest-deep">{farm.name}</p>
                          <p className="text-xs text-soil-muted">
                            {farm.district ? `${farm.district}, ` : ''}
                            {farm.state} · {farm.soil_type || 'Soil unset'} (pH{' '}
                            {farm.soil_ph ?? '—'}) · {farm.irrigation_type || 'mixed'} irrigation
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 sm:gap-3">
                        <div className="mr-1 text-right">
                          <p className="font-mono text-sm font-bold text-soil-charcoal">
                            {farm.area_hectares} ha
                          </p>
                          <p className="text-[11px] font-semibold text-emerald-leaf">
                            {farm.primary_crop || 'Multi-crop'}
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleStartEditFarm(farm)}
                          aria-label={`Edit ${farm.name}`}
                          className="rounded-lg border border-soil-border bg-white p-2 text-soil-muted hover:border-emerald-border hover:bg-emerald-mist/60 hover:text-forest-deep"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteFarm(farm.id, farm.name)}
                          aria-label={`Delete ${farm.name}`}
                          className="rounded-lg border border-soil-border bg-white p-2 text-soil-muted hover:border-red-200 hover:bg-red-50 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
