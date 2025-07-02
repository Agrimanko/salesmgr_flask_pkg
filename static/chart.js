/* chart.js */
let allTimeChart = null;
let filteredChart = null;
let trendChart = null;

function buildAllTimeChart(labels, qtyValues, revenueValues) {
  const ctx = document.getElementById('chartAllTime').getContext('2d');
  
  // Destroy existing chart if it exists
  if (allTimeChart) {
    allTimeChart.destroy();
  }
  
  // Create new chart
  allTimeChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Qty Terjual (All Time)',
          data: qtyValues,
          backgroundColor: 'rgba(75, 192, 192, 0.5)',
          order: 2,
          yAxisID: 'y'
        },
        {
          label: 'Total Penjualan (Rp)',
          data: revenueValues,
          type: 'line',
          borderColor: 'rgba(255, 99, 132, 1)',
          borderWidth: 2,
          fill: false,
          tension: 0.1,
          order: 1,
          yAxisID: 'y1'
        }
      ]
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true,
          position: 'left',
          title: {
            display: true,
            text: 'Qty Terjual'
          }
        },
        y1: {
          beginAtZero: true,
          position: 'right',
          title: {
            display: true,
            text: 'Total Penjualan (Rp)'
          },
          grid: {
            drawOnChartArea: false
          }
        }
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: function(context) {
              let label = context.dataset.label || '';
              if (label === 'Qty Terjual (All Time)') {
                return 'Qty: ' + context.raw;
              } else if (label === 'Total Penjualan (Rp)') {
                return 'Total: Rp ' + new Intl.NumberFormat('id-ID').format(context.raw);
              }
              return label;
            }
          }
        }
      }
    }
  });
}

function buildFilteredChart(labels, qtyValues, revenueValues) {
  const ctx = document.getElementById('chartFiltered').getContext('2d');
  
  // Destroy existing chart if it exists
  if (filteredChart) {
    filteredChart.destroy();
  }
  
  // Create new chart
  filteredChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Qty Terjual (Filtered)',
          data: qtyValues,
          backgroundColor: 'rgba(54,162,235,.5)',
          order: 2,
          yAxisID: 'y'
        },
        {
          label: 'Total Penjualan (Rp)',
          data: revenueValues,
          type: 'line',
          borderColor: 'rgba(255, 99, 132, 1)',
          borderWidth: 2,
          fill: false,
          tension: 0.1,
          order: 1,
          yAxisID: 'y1'
        }
      ]
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true,
          position: 'left',
          title: {
            display: true,
            text: 'Qty Terjual'
          }
        },
        y1: {
          beginAtZero: true,
          position: 'right',
          title: {
            display: true,
            text: 'Total Penjualan (Rp)'
          },
          grid: {
            drawOnChartArea: false
          }
        }
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: function(context) {
              let label = context.dataset.label || '';
              if (label === 'Qty Terjual (Filtered)') {
                return 'Qty: ' + context.raw;
              } else if (label === 'Total Penjualan (Rp)') {
                return 'Total: Rp ' + new Intl.NumberFormat('id-ID').format(context.raw);
              }
              return label;
            }
          }
        }
      }
    }
  });
}

function buildTrendChart(labels, values) {
  const ctx = document.getElementById('trendChart').getContext('2d');
  
  // Destroy existing chart if it exists
  if (trendChart) {
    trendChart.destroy();
  }
  
  // Create new chart
  trendChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Laba (Rp)',
        data: values,
        tension: .3,
        fill: false,
        borderWidth: 2,
        borderColor: 'rgb(75, 192, 192)'
      }]
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true
        }
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: c => 'Laba: Rp ' + new Intl.NumberFormat('id-ID').format(c.parsed.y)
          }
        }
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  console.log("DOM loaded, initializing charts with timestamp:", window.chartTimestamp);
  
  // Build All Time Chart
  if (window.allTimeLabels && window.allTimeLabels.length > 0) {
    console.log("Building All Time chart");
    buildAllTimeChart(window.allTimeLabels, window.allTimeQtyValues, window.allTimeRevenueValues);
  } else {
    console.log("No data for all time chart");
  }
  
  // Build Filtered Chart
  if (window.filteredLabels && window.filteredLabels.length > 0) {
    console.log("Building Filtered chart");
    buildFilteredChart(window.filteredLabels, window.filteredQtyValues, window.filteredRevenueValues);
  } else {
    console.log("No data for filtered chart");
  }
  
  // Build Trend Chart
  if (window.trendLabels && window.trendLabels.length > 0) {
    console.log("Building Trend chart");
    buildTrendChart(window.trendLabels, window.trendValues);
  } else {
    console.log("No data for trend chart");
  }
});