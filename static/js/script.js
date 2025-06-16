// DOM elements
const companySelect = document.getElementById('company-select');
const startDate = document.getElementById('start-date');
const endDate = document.getElementById('end-date');
const generateBtn = document.getElementById('generate-chart');
const downloadBtn = document.getElementById('download-csv');
const loading = document.getElementById('loading');
const csvLoading = document.getElementById('csv-loading');
const chartPlaceholder = document.getElementById('chart-placeholder');
const chartContainer = document.getElementById('chart-container');
const errorMessage = document.getElementById('error-message');
const chartInfo = document.getElementById('chart-info');
const dataPoints = document.getElementById('data-points');
const companyName = document.getElementById('company-name');
const aggregationLevel = document.getElementById('aggregation-level');

// Calculate responsive chart dimensions
function getChartDimensions() {
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;

  // Use almost full viewport width with minimal padding
  const width = Math.max(viewportWidth - 80, 300); // Only 80px total padding

  // Dynamic height based on viewport size - make it taller to accommodate volume
  let height;
  if (viewportHeight >= 1200) {
    height = viewportHeight * 0.8; // 80% of viewport height
  } else if (viewportHeight >= 900) {
    height = viewportHeight * 0.75; // 75% of viewport height
  } else if (viewportHeight >= 700) {
    height = viewportHeight * 0.7; // 70% of viewport height
  } else {
    height = viewportHeight * 0.6; // 60% of viewport height
  }

  return { width, height };
}

// Validate date range
function validateDates() {
  const start = new Date(startDate.value);
  const end = new Date(endDate.value);

  if (start > end) {
    endDate.value = startDate.value;
  }
}

// Determine aggregation level based on date range
function getAggregationLevel(startDate, endDate) {
  const start = new Date(startDate);
  const end = new Date(endDate);
  const diffInDays = Math.ceil((end - start) / (1000 * 60 * 60 * 24));

  if (diffInDays > 365) {
    return 'monthly';
  } else if (diffInDays > 60) {
    return 'weekly';
  } else {
    return 'daily';
  }
}

// Create volume bar colors based on price movement
function getVolumeColors(opens, closes) {
  return opens.map((open, index) => {
    const close = closes[index];
    return close >= open ? '#22c55e' : '#ef4444'; // Green for up, red for down
  });
}

// Create Plotly chart with volume subplot
function createChart(data, companyName, startDate, endDate, aggregation) {
  const dimensions = getChartDimensions();
  const volumeColors = getVolumeColors(data.opens, data.closes);

  // Candlestick trace
  const candlestickTrace = {
    x: data.dates,
    open: data.opens,
    high: data.highs,
    low: data.lows,
    close: data.closes,
    type: 'candlestick',
    name: 'OHLC',
    yaxis: 'y',
    increasing: {
      line: { color: '#22c55e', width: 1 },
      fillcolor: 'rgba(34, 197, 94, 0.3)',
    },
    decreasing: {
      line: { color: '#ef4444', width: 1 },
      fillcolor: 'rgba(239, 68, 68, 0.3)',
    },
    showlegend: false,
  };

  // Volume trace
  const volumeTrace = {
    x: data.dates,
    y: data.volumes,
    type: 'bar',
    name: 'Volume',
    yaxis: 'y2',
    marker: {
      color: volumeColors,
      opacity: 0.7,
    },
    showlegend: false,
  };

  const layout = {
    title: {
      text: `${companyName} Stock Price & Volume (${startDate} to ${endDate}) - ${
        aggregation.charAt(0).toUpperCase() + aggregation.slice(1)
      } Data`,
      font: { color: 'hsl(213, 31%, 91%)', size: 18 },
      y: 0.95,
    },

    // Price chart (main chart)
    yaxis: {
      domain: [0.3, 1], // Takes up 70% of the height (top portion)
      title: {
        text: 'Price ($)',
        font: { color: 'hsl(213, 31%, 91%)' },
      },
      gridcolor: 'rgba(213, 213, 213, 0.1)',
      linecolor: 'hsl(213, 31%, 91%)',
      tickfont: { color: 'hsl(213, 31%, 91%)' },
      side: 'left',
    },

    // Volume chart (bottom subplot)
    yaxis2: {
      domain: [0, 0.25], // Takes up 25% of the height (bottom portion)
      title: {
        text: 'Volume',
        font: { color: 'hsl(213, 31%, 91%)' },
      },
      gridcolor: 'rgba(213, 213, 213, 0.1)',
      linecolor: 'hsl(213, 31%, 91%)',
      tickfont: { color: 'hsl(213, 31%, 91%)' },
      side: 'left',
    },

    // Shared x-axis
    xaxis: {
      title: {
        text: 'Date',
        font: { color: 'hsl(213, 31%, 91%)' },
      },
      gridcolor: 'rgba(213, 213, 213, 0.1)',
      linecolor: 'hsl(213, 31%, 91%)',
      tickfont: { color: 'hsl(213, 31%, 91%)' },
      rangeslider: { visible: false },
      type: 'date',
    },

    plot_bgcolor: 'hsl(222, 47%, 8%)',
    paper_bgcolor: 'hsl(222, 47%, 8%)',
    font: { color: 'hsl(213, 31%, 91%)', size: 12 },
    margin: { l: 80, r: 40, t: 100, b: 80 },
    autosize: true,
    width: dimensions.width,
    height: dimensions.height,

    // Remove gap between subplots
    hovermode: 'x unified',
  };

  const config = {
    displayModeBar: true,
    responsive: true,
    toImageButtonOptions: {
      format: 'png',
      filename: `${companyName}_stock_chart_${aggregation}`,
      height: dimensions.height,
      width: dimensions.width,
      scale: 1,
    },
    modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
  };

  // Create the plot with both traces
  Plotly.newPlot(
    chartContainer,
    [candlestickTrace, volumeTrace],
    layout,
    config
  );

  // Add custom hover behavior for better UX
  chartContainer.on('plotly_hover', function (data) {
    const pointIndex = data.points[0].pointIndex;
    const date = data.points[0].x;
    const formattedDate = new Date(date).toLocaleDateString();

    // You can add custom hover information here if needed
    console.log(`Hovering over ${formattedDate}`);
  });
}

// Resize chart when window is resized
function handleResize() {
  if (
    chartContainer.style.display !== 'none' &&
    chartContainer.hasChildNodes()
  ) {
    const dimensions = getChartDimensions();
    Plotly.relayout(chartContainer, {
      width: dimensions.width,
      height: dimensions.height,
    });
  }
}

// Validate form inputs
function validateInputs() {
  const companyId = companySelect.value;
  const startDateValue = startDate.value;
  const endDateValue = endDate.value;

  if (!companyId) {
    showError('Please select a company');
    return false;
  }

  if (!startDateValue || !endDateValue) {
    showError('Please select both start and end dates');
    return false;
  }

  return true;
}

// Convert data to CSV format
function convertToCSV(data, aggregation) {
  let headers = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'];
  let csvContent = headers.join(',') + '\n';

  for (let i = 0; i < data.dates.length; i++) {
    let row = [
      data.dates[i],
      data.opens[i].toFixed(2),
      data.highs[i].toFixed(2),
      data.lows[i].toFixed(2),
      data.closes[i].toFixed(2),
      data.volumes[i],
    ];
    csvContent += row.join(',') + '\n';
  }

  return csvContent;
}

// Download CSV file
function downloadCSV(csvContent, filename) {
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// Generate chart function
async function generateChart() {
  if (!validateInputs()) return;

  const companyId = companySelect.value;
  const startDateValue = startDate.value;
  const endDateValue = endDate.value;

  // Determine aggregation level
  const aggregation = getAggregationLevel(startDateValue, endDateValue);

  // Show loading
  loading.classList.remove('hidden');
  chartPlaceholder.classList.add('hidden');
  chartContainer.style.display = 'none';
  errorMessage.classList.add('hidden');
  chartInfo.classList.add('hidden');

  try {
    const response = await fetch('/api/chart-data/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify({
        company_id: companyId,
        start_date: startDateValue,
        end_date: endDateValue,
        aggregation: aggregation,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to load chart data');
    }

    // Hide loading
    loading.classList.add('hidden');

    // Show chart container
    chartContainer.style.display = 'block';

    // Create the chart with volume
    createChart(
      data.chart_data,
      data.company_name,
      data.start_date,
      data.end_date,
      data.aggregation
    );

    // Show chart info
    dataPoints.textContent = data.data_points;
    companyName.textContent = data.company_name;
    aggregationLevel.textContent = data.aggregation;
    chartInfo.classList.remove('hidden');

    console.log(
      'Chart loaded successfully with',
      data.data_points,
      'data points',
      '(' + data.aggregation + ' aggregation)'
    );
  } catch (error) {
    console.error('Error loading chart:', error);
    loading.classList.add('hidden');
    showError(error.message);
  }
}

// Download CSV function
async function downloadCSVData() {
  if (!validateInputs()) return;

  const companyId = companySelect.value;
  const startDateValue = startDate.value;
  const endDateValue = endDate.value;

  // Determine aggregation level
  const aggregation = getAggregationLevel(startDateValue, endDateValue);

  // Show CSV loading
  csvLoading.classList.remove('hidden');
  chartPlaceholder.classList.add('hidden');
  errorMessage.classList.add('hidden');

  try {
    const response = await fetch('/api/chart-data/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify({
        company_id: companyId,
        start_date: startDateValue,
        end_date: endDateValue,
        aggregation: aggregation,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to load data');
    }

    // Hide CSV loading
    csvLoading.classList.add('hidden');

    // Convert to CSV and download
    const csvContent = convertToCSV(data.chart_data, data.aggregation);
    const filename = `${data.company_name}_stock_data_${data.aggregation}_${data.start_date}_to_${data.end_date}.csv`;

    downloadCSV(csvContent, filename);

    // Show success message briefly
    const successMsg = document.createElement('div');
    successMsg.className = 'chart-info';
    successMsg.style.backgroundColor = 'var(--success)';
    successMsg.innerHTML = `<p>CSV downloaded successfully: ${data.data_points} data points</p>`;

    if (!chartPlaceholder.classList.contains('hidden')) {
      chartPlaceholder.style.display = 'none';
    }

    document.querySelector('.chart-container').appendChild(successMsg);

    setTimeout(() => {
      successMsg.remove();
      if (chartContainer.style.display === 'none') {
        chartPlaceholder.style.display = 'flex';
      }
    }, 3000);

    console.log(
      'CSV downloaded successfully with',
      data.data_points,
      'data points'
    );
  } catch (error) {
    console.error('Error downloading CSV:', error);
    csvLoading.classList.add('hidden');
    showError(error.message);
  }
}

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.classList.remove('hidden');
  chartPlaceholder.classList.remove('hidden');
  chartContainer.style.display = 'none';
  chartInfo.classList.add('hidden');
}

// Get CSRF token
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + '=') {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Event listeners
startDate.addEventListener('change', validateDates);
endDate.addEventListener('change', validateDates);
generateBtn.addEventListener('click', generateChart);
downloadBtn.addEventListener('click', downloadCSVData);

// Window resize handler with debouncing
let resizeTimeout;
window.addEventListener('resize', function () {
  clearTimeout(resizeTimeout);
  resizeTimeout = setTimeout(handleResize, 250);
});

// Allow Enter key to generate chart
document.addEventListener('keypress', function (e) {
  if (e.key === 'Enter' && companySelect.value) {
    generateChart();
  }
});

// Initial setup
document.addEventListener('DOMContentLoaded', function () {
  // Set initial chart container style
  chartContainer.style.width = '100%';
  chartContainer.style.minHeight = '500px';
});
