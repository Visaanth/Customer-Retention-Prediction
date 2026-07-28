/* ==========================================================================
   Customer Churn Intelligence Web Dashboard - Chart Visualizations Engine
   ========================================================================== */

const DashboardCharts = {
  contractChart: null,
  tenureChart: null,
  chargesChart: null,
  reasonsChart: null,

  initCharts(statsData) {
    this.createContractChart(statsData.contractDistribution);
    this.createTenureChart(statsData.tenureBreakdown);
    this.createChargesChart(statsData.chargesBreakdown);
    this.createReasonsChart(statsData.churnReasons);
  },

  getChartColors() {
    const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
    return {
      textColor: isDark ? '#94a3b8' : '#475569',
      gridColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.08)',
      primary: '#6366f1',
      secondary: '#06b6d4',
      purple: '#a855f7',
      high: '#ef4444',
      medium: '#f59e0b',
      low: '#10b981'
    };
  },

  createContractChart(data = {}) {
    const ctx = document.getElementById('contractChart')?.getContext('2d');
    if (!ctx) return;
    if (this.contractChart) this.contractChart.destroy();

    const colors = this.getChartColors();
    const labels = Object.keys(data).length ? Object.keys(data) : ['Month-to-Month', 'One Year', 'Two Year'];
    const values = Object.values(data).length ? Object.values(data) : [54, 24, 22];

    this.contractChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: [colors.high, colors.medium, colors.low],
          borderWidth: 0,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: colors.textColor, padding: 16, font: { family: 'Inter', size: 12 } }
          },
          tooltip: {
            callbacks: {
              label: (context) => ` ${context.label}: ${context.raw}% Churn Rate`
            }
          }
        },
        cutout: '70%'
      }
    });
  },

  createTenureChart(data = {}) {
    const ctx = document.getElementById('tenureChart')?.getContext('2d');
    if (!ctx) return;
    if (this.tenureChart) this.tenureChart.destroy();

    const colors = this.getChartColors();
    const labels = data.labels || ['0-6 Mo', '6-12 Mo', '12-24 Mo', '24-48 Mo', '48+ Mo'];
    const churned = data.churned || [48, 35, 24, 15, 8];
    const stayed = data.stayed || [52, 65, 76, 85, 92];

    this.tenureChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Churned %',
            data: churned,
            backgroundColor: colors.high,
            borderRadius: 6
          },
          {
            label: 'Retained %',
            data: stayed,
            backgroundColor: colors.low,
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { display: false }, ticks: { color: colors.textColor } },
          y: { grid: { color: colors.gridColor }, ticks: { color: colors.textColor }, max: 100 }
        },
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: colors.textColor, font: { family: 'Inter', size: 12 } }
          }
        }
      }
    });
  },

  createChargesChart(data = {}) {
    const ctx = document.getElementById('chargesChart')?.getContext('2d');
    if (!ctx) return;
    if (this.chargesChart) this.chargesChart.destroy();

    const colors = this.getChartColors();
    const labels = data.labels || ['$20-40', '$40-60', '$60-80', '$80-100', '$100+'];
    const rates = data.rates || [12, 18, 32, 45, 58];

    this.chargesChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Churn Risk Probability (%)',
          data: rates,
          borderColor: colors.primary,
          backgroundColor: 'rgba(99, 102, 241, 0.15)',
          fill: true,
          tension: 0.4,
          pointRadius: 5,
          pointBackgroundColor: colors.purple
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { color: colors.gridColor }, ticks: { color: colors.textColor } },
          y: { grid: { color: colors.gridColor }, ticks: { color: colors.textColor }, max: 100 }
        },
        plugins: {
          legend: { display: false }
        }
      }
    });
  },

  createReasonsChart(data = {}) {
    const ctx = document.getElementById('reasonsChart')?.getContext('2d');
    if (!ctx) return;
    if (this.reasonsChart) this.reasonsChart.destroy();

    const colors = this.getChartColors();
    const labels = data.labels || [
      'Competitor offered higher download speeds',
      'Competitor offered more data',
      'Attitude of support person',
      'Price too high',
      'Network reliability issues'
    ];
    const counts = data.counts || [312, 280, 210, 195, 140];

    this.reasonsChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          axis: 'y',
          label: 'Impacted Customers',
          data: counts,
          backgroundColor: colors.secondary,
          borderRadius: 6
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { color: colors.gridColor }, ticks: { color: colors.textColor } },
          y: { grid: { display: false }, ticks: { color: colors.textColor } }
        },
        plugins: {
          legend: { display: false }
        }
      }
    });
  },

  updateTheme() {
    // Refresh chart theme colors when theme toggle is clicked
    if (this.contractChart) this.contractChart.update();
    if (this.tenureChart) this.tenureChart.update();
    if (this.chargesChart) this.chargesChart.update();
    if (this.reasonsChart) this.reasonsChart.update();
  }
};
