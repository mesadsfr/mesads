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
// The current trimester (ie. the one that is not finished yet) is not included.
function GroupDataByTrimester(data: Record<string, number>) {
  const groupedByTrimester: Record<string, number> = {};
  let last = null;

  Object.keys(data).forEach((key) => {
    const [year, month] = key.split("-").map(Number);
    const trimester = Math.ceil(month / 3);

    const e = trimester === 1 ? "ᵉʳ" : "ᵉ";

    const trimesterKey = `${trimester}${e} trimestre ${year}`;

    if (!groupedByTrimester[trimesterKey]) {
      groupedByTrimester[trimesterKey] = 0;
    }
    groupedByTrimester[trimesterKey] += data[key];
    last = trimesterKey;
  });

  if (last) {
    delete groupedByTrimester[last];
  }

  groupedByTrimester.V;
  return groupedByTrimester;
}

// Given an object where keys are strings and values are numbers, update the values to be the sum of the values of the previous keys.
function AccumulateValues(data: Record<string, number>) {
  // Accumulate values to have a graph that shows the total number of ads over time
  let sum = 0;
  return Object.values(data).reduce((acc: number[], curr: number) => {
    sum += curr;
    acc.push(sum);
    return acc;
  }, []);
}

function DisplayLineChart(
  canvas: HTMLCanvasElement,
  labels: string[],
  data: number[]
) {
  new Chart(canvas, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          data: data,
          borderColor: "rgba(75, 192, 192, 1)",
          borderWidth: 5,
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
        },
      },
    },
  });
}

// The type of data given to this script by the Django template.
type DataType = {
  ads_by_month: Record<string, number>;
  ads_manager_requests_by_month: Record<string, number>;
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

const requestsByTrimester = GroupDataByTrimester(
  data.ads_manager_requests_by_month
);

DisplayLineChart(
  document.getElementById("ads-manager-requests-count") as HTMLCanvasElement,
  Object.keys(requestsByTrimester),
  AccumulateValues(requestsByTrimester)
);
