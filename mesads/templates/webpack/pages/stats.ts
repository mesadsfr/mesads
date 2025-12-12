import {
  CategoryScale,
  Chart,
  LineController,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
} from "chart.js";

Chart.register(
  CategoryScale,
  LineController,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip
);

function DisplayLineChart(
  canvas: HTMLCanvasElement,
  labels: string[],
  data: number[],
  max?: number
) {
  // Case where there are no data points
  if (labels.length === 0 && data.length === 0) {
    labels = ["", ""];
    data = [0, 0];
  }
  // Case where there is only one data point, we duplicate it to have a line.
  else if (labels.length === 1 && data.length === 1) {
    labels = [...labels, "Aujourd'hui"];
    data = [data[0], data[0]];
  }

  // All labels and data except the last one.
  const completedLabels = labels.slice(0, -1);
  const completedData = data.slice(0, -1);

  // Data of the current trimester.
  const currentTrimesterData = data.slice(-1);

  new Chart(canvas, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        // All the completed trimester are displayed as a solid line.
        {
          data: completedData,
          borderColor: "rgba(75, 192, 192, 1)",
          borderWidth: 5,
        },
        // The current trimester is displayed as a dashed line.
        {
          data: [
            ...Array(completedLabels.length - 1).fill(null),
            ...completedData.slice(-1), // The last value of the completed data
            ...currentTrimesterData, // The current trimester data
          ],
          borderColor: "rgba(75, 192, 192, 1)",
          borderWidth: 5,
          borderDash: [5, 10],
        },
      ],
    },
    options: {
      scales: {
        y: {
          beginAtZero: true,
          max: max,
        },
      },
      locale: "fr",
      plugins: {
        tooltip: {
          padding: 20,
          mode: "nearest",
          displayColors: false,
          // Disable the tooltip for the first data point of the current
          // trimester, to avoid showing the tooltip twice, one for the last
          // point of the previous trimesters and one for the first point of the
          // current trimester.
          filter: function (tooltipItem, data) {
            return !(
              tooltipItem.datasetIndex === 1 &&
              tooltipItem.dataIndex === completedData.length - 1
            );
          },
        },
      },
    },
  });
}

// The type of data given to this script by the Django template.
type DataType = {
  ads_by_trimester: Record<string, number>;
  ads_manager_by_trimester: Record<string, number>;
  proprietaire_by_trimester: Record<string, number>;
  vehicule_by_trimester: Record<string, number>;
};

const data = JSON.parse(
  (document.getElementById("data") as HTMLScriptElement).text
) as DataType;

DisplayLineChart(
  document.getElementById("ads-count") as HTMLCanvasElement,
  Object.keys(data.ads_by_trimester),
  Object.values(data.ads_by_trimester),
  // Hardcode the maximum value to 60000, because there are approximately 60000
  // in total. If we don't hardcode the value, the maximum value of the graph
  // corresponds to +- the number of ADS which we registered in the database,
  // which might be confusing.
  60000
);

DisplayLineChart(
  document.getElementById("ads-manager-requests-count") as HTMLCanvasElement,
  Object.keys(data.ads_manager_by_trimester),
  Object.values(data.ads_manager_by_trimester)
);

DisplayLineChart(
  document.getElementById("relais-proprietaires-count") as HTMLCanvasElement,
  Object.keys(data.proprietaire_by_trimester),
  Object.values(data.proprietaire_by_trimester)
);

DisplayLineChart(
  document.getElementById("relais-vehicules-count") as HTMLCanvasElement,
  Object.keys(data.vehicule_by_trimester),
  Object.values(data.vehicule_by_trimester)
);
