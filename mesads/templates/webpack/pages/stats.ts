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

// Given a dict where keys are dates and values are numbers, return a dict where
// keys are trimesters and values are the sum of the values of the corresponding
// dates.
function GroupDataByTrimester(data: Record<string, number>) {
  const groupedByTrimester: Record<string, number> = {};

  Object.keys(data).forEach((key) => {
    const [year, month] = key.split("-").map(Number);
    const trimester = Math.ceil(month / 3);

    const e = trimester === 1 ? "ᵉʳ" : "ᵉ";

    const trimesterKey = `${trimester}${e} trimestre ${year}`;

    if (!groupedByTrimester[trimesterKey]) {
      groupedByTrimester[trimesterKey] = 0;
    }
    groupedByTrimester[trimesterKey] += data[key];
  });
  return groupedByTrimester;
}

// Given an object where keys are strings and values are numbers, update the values to be the sum of the values of the previous keys.
function AccumulateValues(data: Record<string, number>) {
  // Accumulate values to have a graph that shows the total number of ads over time
  let sum = 0;
  const ret = Object.values(data).reduce((acc: number[], curr: number) => {
    sum += curr;
    acc.push(sum);
    return acc;
  }, []);
  return ret;
}

function DisplayLineChart(
  canvas: HTMLCanvasElement,
  labels: string[],
  data: number[]
) {
  // Case where there is only one data point, we duplicate it to have a line.
  if (labels.length === 1 && data.length === 1) {
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
  ads_by_month: Record<string, number>;
  ads_by_month_filtered: Record<string, number>;
  ads_manager_requests_by_month: Record<string, number>;
  ads_manager_requests_by_month_filtered: Record<string, number>;
  relais_proprietaires_by_month: Record<string, number>;
  relais_vehicules_by_month: Record<string, number>;
};

const data = JSON.parse(
  (document.getElementById("data") as HTMLScriptElement).text
) as DataType;

const adsByTimester = GroupDataByTrimester(data.ads_by_month);

DisplayLineChart(
  document.getElementById("ads-count") as HTMLCanvasElement,
  Object.keys(adsByTimester),
  AccumulateValues(adsByTimester)
);

const adsByTimesterFiltered = GroupDataByTrimester(data.ads_by_month_filtered);

DisplayLineChart(
  document.getElementById("ads-count-filtered") as HTMLCanvasElement,
  Object.keys(adsByTimesterFiltered),
  AccumulateValues(adsByTimesterFiltered)
);

const requestsByTrimester = GroupDataByTrimester(
  data.ads_manager_requests_by_month
);

DisplayLineChart(
  document.getElementById("ads-manager-requests-count") as HTMLCanvasElement,
  Object.keys(requestsByTrimester),
  AccumulateValues(requestsByTrimester)
);

const requestsByTrimesterFiltered = GroupDataByTrimester(
  data.ads_manager_requests_by_month_filtered
);

DisplayLineChart(
  document.getElementById(
    "ads-manager-requests-count-filtered"
  ) as HTMLCanvasElement,
  Object.keys(requestsByTrimesterFiltered),
  AccumulateValues(requestsByTrimesterFiltered)
);

const relaisProprietairesByTrimester = GroupDataByTrimester(
  data.relais_proprietaires_by_month
);

DisplayLineChart(
  document.getElementById("relais-proprietaires-count") as HTMLCanvasElement,
  Object.keys(relaisProprietairesByTrimester),
  AccumulateValues(relaisProprietairesByTrimester)
);

const relaisVehiculesByTrimester = GroupDataByTrimester(
  data.relais_vehicules_by_month
);

DisplayLineChart(
  document.getElementById("relais-vehicules-count") as HTMLCanvasElement,
  Object.keys(relaisVehiculesByTrimester),
  AccumulateValues(relaisVehiculesByTrimester)
);
