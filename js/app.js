/* ==========================================================================
   Customer Churn Intelligence Web Dashboard - Application Controller
   ========================================================================== */

const AppState = {
  activeTab: 'overview',
  theme: localStorage.getItem('app-theme') || 'dark',
  customers: [],
  selectedCustomer: null,
  stats: null
};

document.addEventListener('DOMContentLoaded', () => {
  App.init();
});

const App = {
  async init() {
    this.setupTheme();
    this.setupNavigation();
    this.setupPredictorForm();
    this.setupBatchUpload();
    this.setupCustomerSearch();

    await this.loadCustomerData();
    this.renderDashboardStats();
    DashboardCharts.initCharts(AppState.stats || {});
  },

  /* --- Theme Controller --- */
  setupTheme() {
    document.documentElement.setAttribute('data-theme', AppState.theme);
    const themeBtn = document.getElementById('themeToggleBtn');
    if (themeBtn) {
      themeBtn.innerHTML = AppState.theme === 'dark' ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
      themeBtn.addEventListener('click', () => {
        AppState.theme = AppState.theme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', AppState.theme);
        localStorage.setItem('app-theme', AppState.theme);
        themeBtn.innerHTML = AppState.theme === 'dark' ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
        DashboardCharts.updateTheme();
      });
    }
  },

  /* --- Navigation Controller --- */
  setupNavigation() {
    const tabs = document.querySelectorAll('.nav-tab-item');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const targetView = tab.getAttribute('data-tab');
        if (!targetView) return;

        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        document.querySelectorAll('.tab-view').forEach(view => {
          view.classList.remove('active');
        });

        const activeView = document.getElementById(`tab-${targetView}`);
        if (activeView) activeView.classList.add('active');

        AppState.activeTab = targetView;
      });
    });
  },

  /* --- Customer Data Loader & Search --- */
  async loadCustomerData() {
    try {
      // Try API first if python backend is live
      const resp = await fetch('/api/customers').catch(() => null);
      if (resp && resp.ok) {
        AppState.customers = await resp.json();
      } else {
        // Fallback default sample data if standalone static file
        AppState.customers = this.getFallbackCustomers();
      }

      const statsResp = await fetch('/api/stats').catch(() => null);
      if (statsResp && statsResp.ok) {
        AppState.stats = await statsResp.json();
      } else {
        AppState.stats = this.getFallbackStats();
      }
    } catch (e) {
      console.warn("Using offline standalone dataset", e);
      AppState.customers = this.getFallbackCustomers();
      AppState.stats = this.getFallbackStats();
    }
  },

  renderDashboardStats() {
    const stats = AppState.stats || this.getFallbackStats();
    
    document.getElementById('statTotalCustomers').textContent = stats.totalCustomers?.toLocaleString() || '7,043';
    document.getElementById('statChurnRate').textContent = `${(stats.churnRate || 26.5).toFixed(1)}%`;
    document.getElementById('statHighRiskCount').textContent = stats.highRiskCount?.toLocaleString() || '1,869';
    document.getElementById('statRevenueAtRisk').textContent = `$${(stats.revenueAtRisk || 142500).toLocaleString()}`;
  },

  setupCustomerSearch() {
    const searchInput = document.getElementById('customerSearchInput');
    const dropdown = document.getElementById('customerDropdownList');
    if (!searchInput || !dropdown) return;

    const renderItems = (filterText = '') => {
      dropdown.innerHTML = '';
      const filtered = AppState.customers.filter(c => 
        c['Customer ID']?.toLowerCase().includes(filterText.toLowerCase()) ||
        c.City?.toLowerCase().includes(filterText.toLowerCase())
      ).slice(0, 15);

      if (filtered.length === 0) {
        dropdown.innerHTML = '<div class="dropdown-item" style="color: var(--text-muted)">No matching customer found</div>';
        return;
      }

      filtered.forEach(c => {
        const item = document.createElement('div');
        item.className = 'dropdown-item';
        item.innerHTML = `
          <span><b>${c['Customer ID']}</b> (${c.Contract || 'N/A'})</span>
          <span style="color: var(--text-muted)">$${c['Monthly Charge'] || 0}/mo</span>
        `;
        item.addEventListener('click', () => {
          searchInput.value = c['Customer ID'];
          dropdown.classList.remove('active');
          this.selectCustomer(c);
        });
        dropdown.appendChild(item);
      });
    };

    searchInput.addEventListener('focus', () => {
      renderItems(searchInput.value);
      dropdown.classList.add('active');
    });

    searchInput.addEventListener('input', (e) => {
      renderItems(e.target.value);
      dropdown.classList.add('active');
    });

    document.addEventListener('click', (e) => {
      if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.classList.remove('active');
      }
    });

    // Auto-select first customer
    if (AppState.customers.length > 0) {
      this.selectCustomer(AppState.customers[0]);
    }
  },

  selectCustomer(customer) {
    AppState.selectedCustomer = customer;
    
    // Update profile card
    document.getElementById('profileCustId').textContent = customer['Customer ID'] || 'N/A';
    document.getElementById('profileAvatarLetter').textContent = (customer['Customer ID'] || 'C').charAt(0);
    document.getElementById('profileTenure').textContent = `${customer['Tenure in Months'] || 0} Months`;
    document.getElementById('profileContract').textContent = customer['Contract'] || 'Month-to-month';
    document.getElementById('profileMonthlyCharge').textContent = `$${customer['Monthly Charge'] || 0}`;
    document.getElementById('profileInternetType').textContent = customer['Internet Type'] || 'Fiber Optic';
    document.getElementById('profileCity').textContent = customer['City'] || 'Los Angeles';
    document.getElementById('profileTechSupport').textContent = customer['Premium Tech Support'] || 'No';

    // Calculate prediction score
    const riskScore = this.calculateRiskScore(customer);
    this.updateGaugeMeter(riskScore);
    this.updateRetentionRecommendation(customer, riskScore);
    this.updateRiskFactors(customer);
  },

  /* --- Risk Calculation Engine --- */
  calculateRiskScore(c) {
    let score = 0.25; // baseline

    // Contract impact
    const contract = c['Contract'] || c['contract'] || 'Month-to-month';
    if (contract === 'Month-to-month') score += 0.35;
    else if (contract === 'One Year') score += 0.05;
    else if (contract === 'Two Year') score -= 0.15;

    // Tenure impact
    const tenure = parseFloat(c['Tenure in Months'] || c['tenure'] || 12);
    if (tenure < 6) score += 0.25;
    else if (tenure < 12) score += 0.15;
    else if (tenure > 36) score -= 0.20;

    // Monthly Charges & Internet Type
    const monthly = parseFloat(c['Monthly Charge'] || c['monthlyCharge'] || 70);
    if (monthly > 85) score += 0.15;

    const internet = c['Internet Type'] || c['internetType'] || 'Fiber Optic';
    if (internet === 'Fiber Optic') score += 0.10;

    // Tech Support
    const techSupport = c['Premium Tech Support'] || c['techSupport'] || 'No';
    if (techSupport === 'No') score += 0.10;

    // Paperless Billing
    const paperless = c['Paperless Billing'] || c['paperless'] || 'Yes';
    if (paperless === 'Yes') score += 0.05;

    return Math.min(Math.max(score, 0.05), 0.98);
  },

  updateGaugeMeter(prob) {
    const percent = Math.round(prob * 100);
    const gaugeFill = document.getElementById('gaugeFill');
    const gaugePercent = document.getElementById('gaugePercent');
    const riskBadge = document.getElementById('riskBadge');

    if (gaugePercent) gaugePercent.textContent = `${percent}%`;

    // 180 deg max rotation
    const rotation = (prob * 180);
    if (gaugeFill) gaugeFill.style.transform = `rotate(${rotation}deg)`;

    if (riskBadge) {
      if (prob > 0.70) {
        riskBadge.className = 'risk-alert-badge risk-alert-high';
        riskBadge.innerHTML = `<i class="fas fa-exclamation-triangle"></i> CRITICAL RISK (${percent}%)`;
      } else if (prob > 0.40) {
        riskBadge.className = 'risk-alert-badge risk-alert-medium';
        riskBadge.innerHTML = `<i class="fas fa-exclamation-circle"></i> MODERATE RISK (${percent}%)`;
      } else {
        riskBadge.className = 'risk-alert-badge risk-alert-low';
        riskBadge.innerHTML = `<i class="fas fa-check-circle"></i> LOW RISK (${percent}%)`;
      }
    }
  },

  updateRetentionRecommendation(c, prob) {
    const boxText = document.getElementById('recommendationText');
    if (!boxText) return;

    const contract = c['Contract'] || 'Month-to-month';
    const tenure = parseFloat(c['Tenure in Months'] || 12);
    const internet = c['Internet Type'] || 'Fiber Optic';
    const techSupport = c['Premium Tech Support'] || 'No';

    let action = '';
    if (contract === 'Month-to-month') {
      action = "Customer is on a flexible Month-to-Month contract. Offer a 15% discount on an annual commitment plan to lock in loyalty.";
    } else if (tenure < 12) {
      action = "New customer with low tenure. Schedule a proactive onboarding welcome call and offer a complimentary 3-month speed upgrade.";
    } else if (techSupport === 'No') {
      action = "High monthly charges without tech support. Provide a free 6-month trial of Premium Tech Support and a bill optimization review.";
    } else if (internet === 'Fiber Optic' && prob > 0.5) {
      action = "Fiber Optic subscriber showing high churn probability. Check for local network outages and offer a $10 monthly credit.";
    } else {
      action = "Maintain high engagement with a quarterly satisfaction check-in and loyalty rewards program.";
    }

    boxText.textContent = action;
  },

  updateRiskFactors(c) {
    const container = document.getElementById('riskFactorsList');
    if (!container) return;

    const factors = [
      { name: 'Month-to-Month Contract', impact: c.Contract === 'Month-to-month' ? 'High (+35%)' : 'Low', high: c.Contract === 'Month-to-month' },
      { name: 'Low Tenure (< 12 Mo)', impact: parseFloat(c['Tenure in Months'] || 24) < 12 ? 'High (+25%)' : 'Low', high: parseFloat(c['Tenure in Months'] || 24) < 12 },
      { name: 'High Monthly Charges (>$85)', impact: parseFloat(c['Monthly Charge'] || 50) > 85 ? 'Medium (+15%)' : 'Low', high: parseFloat(c['Monthly Charge'] || 50) > 85 },
      { name: 'No Premium Tech Support', impact: c['Premium Tech Support'] === 'No' ? 'Medium (+10%)' : 'Low', high: c['Premium Tech Support'] === 'No' }
    ];

    container.innerHTML = factors.map(f => `
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.6rem 0; border-bottom: 1px solid var(--border-color)">
        <span style="font-size: 0.875rem; color: var(--text-main)">${f.name}</span>
        <span class="status-badge" style="background: ${f.high ? 'var(--risk-high-bg)' : 'var(--risk-low-bg)'}; color: ${f.high ? 'var(--risk-high)' : 'var(--risk-low)'}; border-color: ${f.high ? 'var(--risk-high-border)' : 'var(--risk-low-border)'}">
          ${f.impact}
        </span>
      </div>
    `).join('');
  },

  /* --- Real-Time Predictor Form Controller --- */
  setupPredictorForm() {
    const form = document.getElementById('livePredictorForm');
    if (!form) return;

    // Synchronize slider output badges
    ['tenure', 'monthlyCharge', 'avgGb'].forEach(id => {
      const input = document.getElementById(id);
      const output = document.getElementById(`${id}Value`);
      if (input && output) {
        input.addEventListener('input', () => {
          output.textContent = id === 'monthlyCharge' ? `$${input.value}` : (id === 'tenure' ? `${input.value} Mo` : `${input.value} GB`);
          this.runLivePrediction();
        });
      }
    });

    // Listen to form input changes
    form.addEventListener('input', () => this.runLivePrediction());
    this.runLivePrediction();
  },

  runLivePrediction() {
    const tenure = parseFloat(document.getElementById('tenure')?.value || 12);
    const monthlyCharge = parseFloat(document.getElementById('monthlyCharge')?.value || 70);
    const contract = document.getElementById('contractSelect')?.value || 'Month-to-month';
    const internetType = document.getElementById('internetSelect')?.value || 'Fiber Optic';
    const techSupport = document.getElementById('techSupportSelect')?.value || 'No';

    const customerObj = {
      'Tenure in Months': tenure,
      'Monthly Charge': monthlyCharge,
      'Contract': contract,
      'Internet Type': internetType,
      'Premium Tech Support': techSupport
    };

    const prob = this.calculateRiskScore(customerObj);
    const percent = Math.round(prob * 100);

    const liveResultPercent = document.getElementById('liveResultPercent');
    const liveResultBadge = document.getElementById('liveResultBadge');
    const liveActionBox = document.getElementById('liveActionBox');

    if (liveResultPercent) liveResultPercent.textContent = `${percent}%`;

    if (liveResultBadge) {
      if (prob > 0.70) {
        liveResultBadge.className = 'risk-alert-badge risk-alert-high';
        liveResultBadge.innerHTML = `<i class="fas fa-exclamation-triangle"></i> HIGH RISK`;
      } else if (prob > 0.40) {
        liveResultBadge.className = 'risk-alert-badge risk-alert-medium';
        liveResultBadge.innerHTML = `<i class="fas fa-exclamation-circle"></i> MODERATE RISK`;
      } else {
        liveResultBadge.className = 'risk-alert-badge risk-alert-low';
        liveResultBadge.innerHTML = `<i class="fas fa-check-circle"></i> LOW RISK`;
      }
    }

    if (liveActionBox) {
      let action = "Standard Customer Maintenance";
      if (contract === 'Month-to-month') action = "Proactively pitch a 1-year contract extension with 10% monthly rebate.";
      else if (tenure < 6) action = "High early-churn risk: Assign welcome account executive for consultation.";
      else if (monthlyCharge > 90) action = "Offer bundle optimization to prevent price-sensitivity churn.";
      liveActionBox.textContent = action;
    }
  },

  /* --- CSV Batch Upload Controller --- */
  setupBatchUpload() {
    const dropzone = document.getElementById('csvDropzone');
    const fileInput = document.getElementById('csvFileInput');
    const tableContainer = document.getElementById('batchResultsContainer');
    const tableBody = document.getElementById('batchResultsTableBody');

    if (!dropzone || !fileInput) return;

    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      if (e.dataTransfer.files.length) {
        this.processBatchCSV(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files.length) {
        this.processBatchCSV(fileInput.files[0]);
      }
    });
  },

  processBatchCSV(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target.result;
      const lines = text.split('\n').filter(l => l.trim());
      if (lines.length < 2) return;

      const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));
      const rows = lines.slice(1, 50).map((line, idx) => {
        const values = line.split(',').map(v => v.trim().replace(/^"|"$/g, ''));
        const rowObj = {};
        headers.forEach((h, i) => rowObj[h] = values[i]);
        rowObj['Customer ID'] = rowObj['Customer ID'] || `CUST-${1000 + idx}`;
        return rowObj;
      });

      this.renderBatchTable(rows);
    };
    reader.readAsText(file);
  },

  renderBatchTable(rows) {
    const tableContainer = document.getElementById('batchResultsContainer');
    const tableBody = document.getElementById('batchResultsTableBody');
    if (!tableContainer || !tableBody) return;

    tableBody.innerHTML = rows.map(r => {
      const prob = this.calculateRiskScore(r);
      const percent = Math.round(prob * 100);
      let riskBadge = `<span class="status-badge" style="background: var(--risk-low-bg); color: var(--risk-low); border-color: var(--risk-low-border)">LOW (${percent}%)</span>`;
      if (prob > 0.7) {
        riskBadge = `<span class="status-badge" style="background: var(--risk-high-bg); color: var(--risk-high); border-color: var(--risk-high-border)">HIGH (${percent}%)</span>`;
      } else if (prob > 0.4) {
        riskBadge = `<span class="status-badge" style="background: var(--risk-medium-bg); color: var(--risk-medium); border-color: var(--risk-medium-border)">MED (${percent}%)</span>`;
      }

      return `
        <tr>
          <td><b>${r['Customer ID']}</b></td>
          <td>${r['Tenure in Months'] || r.Tenure || '12'} Mo</td>
          <td>${r['Contract'] || 'Month-to-month'}</td>
          <td>$${r['Monthly Charge'] || r.MonthlyCharge || '70'}</td>
          <td>${r['Internet Type'] || 'Fiber Optic'}</td>
          <td>${riskBadge}</td>
        </tr>
      `;
    }).join('');

    tableContainer.style.display = 'block';
  },

  /* --- Sample Standalone Data --- */
  getFallbackCustomers() {
    return [
      { 'Customer ID': '7590-VHVEG', 'Tenure in Months': 1, 'Contract': 'Month-to-month', 'Monthly Charge': 29.85, 'Internet Type': 'DSL', 'City': 'Los Angeles', 'Premium Tech Support': 'No' },
      { 'Customer ID': '5575-GNVDE', 'Tenure in Months': 34, 'Contract': 'One Year', 'Monthly Charge': 56.95, 'Internet Type': 'DSL', 'City': 'San Diego', 'Premium Tech Support': 'Yes' },
      { 'Customer ID': '3668-QVRHG', 'Tenure in Months': 2, 'Contract': 'Month-to-month', 'Monthly Charge': 53.85, 'Internet Type': 'DSL', 'City': 'San Jose', 'Premium Tech Support': 'No' },
      { 'Customer ID': '7795-CFOCW', 'Tenure in Months': 45, 'Contract': 'One Year', 'Monthly Charge': 42.30, 'Internet Type': 'DSL', 'City': 'San Francisco', 'Premium Tech Support': 'Yes' },
      { 'Customer ID': '9237-HQJSL', 'Tenure in Months': 2, 'Contract': 'Month-to-month', 'Monthly Charge': 70.70, 'Internet Type': 'Fiber Optic', 'City': 'Fresno', 'Premium Tech Support': 'No' },
      { 'Customer ID': '9305-CDSKC', 'Tenure in Months': 8, 'Contract': 'Month-to-month', 'Monthly Charge': 99.65, 'Internet Type': 'Fiber Optic', 'City': 'Sacramento', 'Premium Tech Support': 'No' },
      { 'Customer ID': '1452-KNGWZ', 'Tenure in Months': 22, 'Contract': 'Month-to-month', 'Monthly Charge': 89.10, 'Internet Type': 'Fiber Optic', 'City': 'Long Beach', 'Premium Tech Support': 'No' },
      { 'Customer ID': '6713-OKOMC', 'Tenure in Months': 10, 'Contract': 'Month-to-month', 'Monthly Charge': 29.75, 'Internet Type': 'DSL', 'City': 'Oakland', 'Premium Tech Support': 'No' },
      { 'Customer ID': '7892-POOKP', 'Tenure in Months': 28, 'Contract': 'Month-to-month', 'Monthly Charge': 104.80, 'Internet Type': 'Fiber Optic', 'City': 'Bakersfield', 'Premium Tech Support': 'Yes' },
      { 'Customer ID': '6388-TABGU', 'Tenure in Months': 62, 'Contract': 'One Year', 'Monthly Charge': 56.15, 'Internet Type': 'DSL', 'City': 'Anaheim', 'Premium Tech Support': 'No' }
    ];
  },

  getFallbackStats() {
    return {
      totalCustomers: 7043,
      churnRate: 26.5,
      highRiskCount: 1869,
      revenueAtRisk: 142500,
      contractDistribution: { 'Month-to-Month': 55, 'One Year': 24, 'Two Year': 21 },
      tenureBreakdown: {
        labels: ['0-6 Mo', '6-12 Mo', '12-24 Mo', '24-48 Mo', '48+ Mo'],
        churned: [52, 38, 25, 14, 7],
        stayed: [48, 62, 75, 86, 93]
      },
      chargesBreakdown: {
        labels: ['$20-40', '$40-60', '$60-80', '$80-100', '$100+'],
        rates: [10, 16, 30, 48, 62]
      },
      churnReasons: {
        labels: [
          'Competitor offered higher download speeds',
          'Competitor offered more data',
          'Attitude of support person',
          'Price too high',
          'Network reliability issues'
        ],
        counts: [312, 280, 210, 195, 140]
      }
    };
  }
};
