import { describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { AppRoutes } from '../App';
import { AuthProvider } from '../context/AuthContext';
import { ToastProvider } from '../context/ToastContext';

function renderAt(initialRoute: string) {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <ToastProvider>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </ToastProvider>
    </MemoryRouter>
  );
}

async function signInAsDemoFarmer() {
  const user = userEvent.setup();
  const demoBtn = await screen.findByRole('button', { name: /Demo Farmer View/i });
  await user.click(demoBtn);
  await screen.findByText(/Farm Telemetry Summary/i);
  return user;
}

async function signInAsDemoAdmin() {
  const user = userEvent.setup();
  const adminBtn = await screen.findByRole('button', { name: /Demo Admin View/i });
  await user.click(adminBtn);
  await screen.findByText(/Role-Restricted Administration View/i);
  return user;
}

describe('TerraQora AI — Phase 3 Frontend Suite', () => {
  it('renders Landing Page with brand identity and CTAs', () => {
    renderAt('/');
    expect(screen.getAllByText(/TerraQora/i).length).toBeGreaterThan(0);
    expect(screen.getByRole('heading', { level: 1, name: /Every Acre\./i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Launch Farmer Platform/i })).toBeInTheDocument();
  });

  it('redirects unauthenticated access on protected route to /auth and validates login form', async () => {
    renderAt('/dashboard');
    expect(await screen.findByText(/Welcome back/i)).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /Sign In to TerraQora AI/i }));
    expect(await screen.findByText(/valid email address/i)).toBeInTheDocument();
  });

  it('supports registration tab validation and farmer account creation', async () => {
    renderAt('/auth?mode=register');
    expect(await screen.findByText(/Register your farm workspace/i)).toBeInTheDocument();

    const user = userEvent.setup();
    fireEvent.change(screen.getByLabelText(/Full Name/i), {
      target: { value: 'Kavitha Rajan' },
    });
    fireEvent.change(screen.getByLabelText(/Email Address/i), {
      target: { value: 'kavitha@farm.in' },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: 'StrongPass#2026' },
    });
    await user.click(screen.getByRole('button', { name: /Create Farmer Account/i }));
    expect(await screen.findByText(/Farm Telemetry Summary/i)).toBeInTheDocument();
  });

  it('allows Demo Farmer sandbox login, displays dashboard, and hides admin console', async () => {
    renderAt('/auth');
    await signInAsDemoFarmer();
    expect(screen.getByText(/Pollachi North Plot A/i)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Admin Console/i })).not.toBeInTheDocument();
  });

  it('redirects farmer accounts away from /admin back to /dashboard', async () => {
    renderAt('/auth');
    await signInAsDemoFarmer();
    cleanup();
    // Hydrate existing farmer session directly on /admin and verify role guard redirect
    renderAt('/admin');
    expect(await screen.findByText(/Farm Telemetry Summary/i)).toBeInTheDocument();
    expect(screen.queryByText(/ML & Computer Vision Model Registry/i)).not.toBeInTheDocument();
  });

  it('allows Demo Admin login and renders Admin Console with model registry and user filter', async () => {
    renderAt('/auth');
    const user = await signInAsDemoAdmin();
    expect(screen.getByText(/ML & Computer Vision Model Registry/i)).toBeInTheDocument();

    const usersTable = screen.getByRole('table', { name: /Platform Users Directory/i });
    expect(within(usersTable).getByText(/Dr\. Karthik Menon/i)).toBeInTheDocument();

    const searchInput = screen.getByLabelText(/Search users/i);
    await user.type(searchInput, 'Raghavendra');
    expect(within(usersTable).getByText(/Raghavendra Rao/i)).toBeInTheDocument();
    expect(within(usersTable).queryByText(/Dr\. Karthik Menon/i)).not.toBeInTheDocument();
  });

  it('validates leak-free Crop Yield Prediction form (no Production input) and handles Coconut nuts/ha units', async () => {
    renderAt('/auth');
    const user = await signInAsDemoFarmer();

    await user.click(screen.getByRole('link', { name: /Yield Prediction/i }));
    expect(await screen.findByText(/Field & Seasonal Parameters/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Total Production/i)).not.toBeInTheDocument();

    const cropSelect = screen.getByLabelText(/Crop \(55 Dataset Crops\)/i);
    await user.selectOptions(cropSelect, 'Coconut');

    await user.click(screen.getByRole('button', { name: /Predict Crop Yield/i }));
    expect(await screen.findByText(/Predicted Unit Yield/i)).toBeInTheDocument();
    expect((await screen.findAllByText(/nuts\/hectare/i)).length).toBeGreaterThanOrEqual(2);
  });

  it('validates Plant Disease upload file type/size and renders low-confidence uncertainty warning', async () => {
    renderAt('/auth');
    const user = await signInAsDemoFarmer();

    await user.click(screen.getByRole('link', { name: /Plant Disease CV/i }));
    const fileInput = await screen.findByLabelText(/Click to choose or drag/i);

    const badFile = new File(['hello'], 'notes.txt', { type: 'text/plain' });
    fireEvent.change(fileInput, { target: { files: [badFile] } });
    expect(await screen.findByText(/Unsupported file format/i)).toBeInTheDocument();

    const uncertainLeaf = new File(['tiny-bytes'], 'unknown_leaf.jpg', { type: 'image/jpeg' });
    fireEvent.change(fileInput, { target: { files: [uncertainLeaf] } });
    await user.click(screen.getByRole('button', { name: /Detect Plant Disease/i }));

    expect(
      await screen.findByText(/Uncertain Classification Warning/i)
    ).toBeInTheDocument();
  });

  it('computes Smart Fertilizer Plan and Crop Recommendation suitability results', async () => {
    renderAt('/auth');
    const user = await signInAsDemoFarmer();

    await user.click(screen.getByRole('link', { name: /Smart Fertilizer/i }));
    await user.click(await screen.findByRole('button', { name: /Recommend Fertilizer/i }));
    expect(await screen.findByText(/Recommended Formulation/i)).toBeInTheDocument();

    await user.click(screen.getByRole('link', { name: /Crop Suitability/i }));
    await user.click(
      await screen.findByRole('button', { name: /Find Best Suitable Crops/i })
    );
    expect(await screen.findByText(/Primary Crop Match/i)).toBeInTheDocument();
  });

  it('renders Weather & Irrigation page with explicit non-sensor weather notice', async () => {
    renderAt('/auth');
    const user = await signInAsDemoFarmer();

    await user.click(screen.getByRole('link', { name: /Weather & Irrigation/i }));
    expect(
      await screen.findByText(/Weather-Estimated Advisory Only/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/7-Day Rainfall vs\. Max Temperature Forecast/i)).toBeInTheDocument();
  });

  it('supports 5-language GenAI Farming Assistant chat flow and clearing messages', async () => {
    renderAt('/auth');
    const user = await signInAsDemoFarmer();

    await user.click(screen.getByRole('link', { name: /GenAI Assistant/i }));
    const langSelect = await screen.findByLabelText(/Assistant Language/i);
    await user.selectOptions(langSelect, 'ta');

    const chatInput = screen.getByLabelText(/Ask TerraQora AI Advisor/i);
    await user.type(chatInput, 'Paddy leaf tip yellowing guidance?');
    await user.click(screen.getByRole('button', { name: /^Send$/i }));

    const echoedMessages = await screen.findAllByText(
      /Paddy leaf tip yellowing guidance\?/i
    );
    expect(echoedMessages.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/முன்னோட்ட முறை/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Clear Chat/i }));
    expect(
      await screen.findByText(/Start a grounded agricultural conversation/i)
    ).toBeInTheDocument();
  });

  it('loads Agriculture Analytics charts, filters, and correlation matrix', async () => {
    renderAt('/auth');
    const user = await signInAsDemoFarmer();

    await user.click(screen.getByRole('link', { name: /Agri Analytics/i }));
    expect(await screen.findByText(/Feature Correlation Matrix/i)).toBeInTheDocument();

    const cropFilter = screen.getByLabelText(/Crop Filter/i);
    await user.selectOptions(cropFilter, 'Coconut');
    await user.click(screen.getByRole('button', { name: /^Apply$/i }));
    expect(await screen.findByText(/8652\.00 nuts\/ha/i)).toBeInTheDocument();
  });

  it('generates and previews AI Farm Report on /reports', async () => {
    renderAt('/auth');
    const user = await signInAsDemoFarmer();

    await user.click(screen.getByRole('link', { name: /AI Reports/i }));
    const titleInput = await screen.findByLabelText(/Report Title/i);
    fireEvent.change(titleInput, { target: { value: 'Erode Turmeric Pre-Sowing Report' } });
    await user.click(screen.getByRole('button', { name: /Generate AI Report/i }));

    expect(
      (await screen.findAllByText(/Erode Turmeric Pre-Sowing Report/i)).length
    ).toBeGreaterThanOrEqual(2);
    await user.click(screen.getByRole('button', { name: /Print \/ Save as PDF/i }));
    expect(window.print).toHaveBeenCalled();
  });

  it('updates Farmer Profile settings and performs Farm Plot Create, Update & Delete CRUD on /profile', async () => {
    renderAt('/auth');
    const user = await signInAsDemoFarmer();

    await user.click(screen.getByRole('link', { name: /Profile & Farms/i }));
    const saveProfileBtn = await screen.findByRole('button', { name: /Save Profile Settings/i });
    const profileForm = saveProfileBtn.closest('form')!;
    const districtInput = within(profileForm).getByLabelText(/District/i);
    fireEvent.change(districtInput, { target: { value: 'Salem' } });
    await user.click(saveProfileBtn);
    expect(
      await screen.findByText(/Farmer profile updated successfully/i)
    ).toBeInTheDocument();

    const farmNameInput = screen.getByLabelText(/Plot \/ Farm Name/i);
    fireEvent.change(farmNameInput, { target: { value: 'Salem West Terrace' } });
    await user.click(screen.getByRole('button', { name: /Add Farm Plot/i }));

    const editBtn = await screen.findByRole('button', {
      name: /Edit Salem West Terrace/i,
    });
    await user.click(editBtn);
    fireEvent.change(screen.getByLabelText(/Plot \/ Farm Name/i), {
      target: { value: 'Salem North Terrace' },
    });
    await user.click(screen.getByRole('button', { name: /Save Farm Changes/i }));

    const delBtn = await screen.findByRole('button', {
      name: /Delete Salem North Terrace/i,
    });
    expect(delBtn).toBeInTheDocument();
    await user.click(delBtn);
    await waitFor(() => {
      expect(
        screen.queryByRole('button', { name: /Delete Salem North Terrace/i })
      ).not.toBeInTheDocument();
    });
  });
});
