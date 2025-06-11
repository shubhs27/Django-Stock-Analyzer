// DOM elements
const companySelect = document.getElementById('company-select');
const startDate = document.getElementById('start-date');
const endDate = document.getElementById('end-date');
const generateBtn = document.getElementById('generate-chart');
const loading = document.getElementById('loading');
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

  // Dynamic height based on viewport size - make it taller
  let height;
  if (viewportHeight >= 1200) {
    height = viewportHeight * 0.7; // 70% of viewport height
  } else if (viewportHeight >= 900) {
    height = viewportHeight * 0.65; // 65% of viewport height
  } else if (viewportHeight >= 700) {
    height = viewportHeight * 0.6; // 60% of viewport height
  } else {
    height = viewportHeight * 0.5; // 50% of viewport height
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

// Create Plotly chart with responsive sizing
function createChart(data, companyName, startDate, endDate, aggregation) {
  const dimensions = getChartDimensions();

  const trace = {
    x: data.dates,
    open: data.opens,
    high: data.highs,
    low: data.lows,
    close: data.closes,
    type: 'candlestick',
    name: 'OHLC',
    increasing: {
      line: { color: '#22c55e' },
      fillcolor: 'rgba(34, 197, 94, 0.3)',
    },
    decreasing: {
      line: { color: '#ef4444' },
      fillcolor: 'rgba(239, 68, 68, 0.3)',
    },
  };

  const layout = {
    title: {
      text: `${companyName} Stock Price (${startDate} to ${endDate}) - ${
        aggregation.charAt(0).toUpperCase() + aggregation.slice(1)
      } Data`,
      font: { color: 'hsl(213, 31%, 91%)' },
    },
    xaxis: {
      title: 'Date',
      gridcolor: 'rgba(213, 213, 213, 0.1)',
      linecolor: 'hsl(213, 31%, 91%)',
      tickfont: { color: 'hsl(213, 31%, 91%)' },
      titlefont: { color: 'hsl(213, 31%, 91%)' },
    },
    yaxis: {
      title: 'Price ($)',
      gridcolor: 'rgba(213, 213, 213, 0.1)',
      linecolor: 'hsl(213, 31%, 91%)',
      tickfont: { color: 'hsl(213, 31%, 91%)' },
      titlefont: { color: 'hsl(213, 31%, 91%)' },
    },
    plot_bgcolor: 'hsl(222, 47%, 8%)',
    paper_bgcolor: 'hsl(222, 47%, 8%)',
    font: { color: 'hsl(213, 31%, 91%)', size: 12 },
    margin: { l: 80, r: 40, t: 100, b: 80 },
    showlegend: false,
    xaxis_rangeslider_visible: false,
    autosize: true,
    width: dimensions.width,
    height: dimensions.height,
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
  };

  Plotly.newPlot(chartContainer, [trace], layout, config);
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

// Generate chart function
async function generateChart() {
  const companyId = companySelect.value;
  const startDateValue = startDate.value;
  const endDateValue = endDate.value;

  // Validation
  if (!companyId) {
    showError('Please select a company');
    return;
  }

  if (!startDateValue || !endDateValue) {
    showError('Please select both start and end dates');
    return;
  }

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

    // Create the chart
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
  chartContainer.style.minHeight = '400px';
});
