import * as L from "leaflet";

const map = L.map("map_ads", { zoomControl: false }).setView(
  [46.2276, 2.2137],
  6
);

type APIProps = {
  code_insee: string;
  nom: string;
  nuts3: string;
  wikipedia: string;
  ads_count: number;
  expected_ads_count: number;
  ads_completee_pourcentage: number;
};

type APIResponse = GeoJSON.FeatureCollection<GeoJSON.Polygon, APIProps>;

// Add credits to map
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution:
    '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);

/* Info box on the top right */
class InfoBox extends L.Control {
  _div: HTMLDivElement;

  constructor() {
    super({ position: "topright" });
    this._div = L.DomUtil.create("div", "leaflet-info");
  }

  onAdd = () => {
    this.update(null);
    return this._div;
  };

  update = (props: APIProps | null) => {
    const title = props ? `${props.nom} (${props.code_insee})` : `Nombre d'ADS`;
    const content = props
      ? this.getInfoboxContent(
          props.ads_count,
          props.expected_ads_count,
          props.ads_completee_pourcentage
        )
      : `Survolez un département pour <br/>afficher le nombre d'ADS enregistrées`;
    this._div.innerHTML = `
          <div class="fr-tile fr-enlarge-link fr-tile--horizontal" style="opacity: 0.8">
            <div class="fr-tile__body">
                <h4 class="fr-tile__title">${title}</h4>
                <p class="fr-tile__desc">${content}</p>
            </div>
        </div>
        `;
  };

  getInfoboxContent = (
    ads_count: number,
    expected_ads_count: number,
    ads_completee_pourcentage: number
  ) => {
    const infos = [
      `&rarr; ${ads_count} ADS ${
        ads_count > 1 ? "enregistrées" : "enregistrée"
      }`,
    ];
    if (expected_ads_count !== null) {
      infos.push(
        `&rarr; ${expected_ads_count} ADS au total <br />dans la préfecture (estimation)`
      );
      infos.push(
        `<div class="fr-mt-1w"><strong>Taux de remplissage: ${Math.round(
          (ads_count / expected_ads_count) * 100
        )}%</strong></div>`
      );
    } else {
      infos.push("Nombre d'ADS total inconnu pour cette préfecture");
    }
    infos.push(
      `<div><strong>Taux de vérification des ADS remplies: ${ads_completee_pourcentage}%</strong></div>`
    );
    return infos.join("<br />");
  };
}

function displayStatsMap(data: APIResponse) {
  const unknown_color = "#0000FF";

  const colors = new Map([
    [0, "#A0A0A0"],
    [1, "#FF0000"],
    [30, "#FFA500"],
    [70, "#00FF00"],
  ]);

  const getFillColor = (ads_count: number, expected_ads_count: number) => {
    if (expected_ads_count === null) {
      if (ads_count) {
        return unknown_color;
      } else {
        return colors.get(0);
      }
    }
    const pct_filled = (ads_count / (expected_ads_count || 0)) * 100;
    const rsorted = Array.from(colors.keys())
      .sort((a, b) => a - b)
      .reverse();
    const key = rsorted.find((e) => pct_filled - e >= 0);
    return colors.get(key || 0);
  };

  const info = new InfoBox().addTo(map);

  const geojson = L.geoJSON(data, {
    style: (feature) => {
      return {
        fillColor: getFillColor(
          feature?.properties.ads_count,
          feature?.properties.expected_ads_count
        ),
        fillOpacity: 0.5,
        color: "#777",
        weight: 1,
      };
    },
    onEachFeature: (feature, layer: L.GeoJSON) => {
      layer.on({
        mouseover: () => {
          layer.setStyle({
            fillOpacity: 1,
          });
          info.update(feature.properties);
        },
        mouseout: (e) => {
          geojson.resetStyle(e.target);
          info.update(null);
        },
        click: () => {
          map.fitBounds(layer.getBounds());
          info.update(feature.properties);
          window.location.href = `#prefecture_${feature.properties.code_insee}`;
        },
      });
    },
  }).addTo(map);

  const legend = new L.Control({ position: "bottomright" });

  legend.onAdd = () => {
    const div = L.DomUtil.create("div");
    const grades = Array.from(colors.keys()).sort((a, b) => a - b);
    let description = `
        <ul class="fr-tile__desc fr-p-0" style="display: flex; flex-direction: column; gap: 5px;">`;
    description += `
          <li class="fr-grid-row fr-grid-row--bottom">
            <i class="fr-mr-3v" style="background:${unknown_color}; width: 24px; height: 24px;"></i>
            Taux de remplissage inconnu
          </li>
        `;
    for (let i = 0; i < grades.length; i++) {
      const label = i === 0 ? "Aucune ADS enregistrée" : `≥ ${grades[i]}%`;
      description += `
            <li class="fr-grid-row fr-grid-row--bottom">
              <i class="fr-mr-3v" style="background:${colors.get(
                grades[i]
              )}; width: 24px; height: 24px;"></i>
              ${label}
            </li>
          `;
    }
    description += "</ul>";
    div.innerHTML = `
      <div class="fr-tile fr-enlarge-link fr-tile--horizontal" style="opacity: 0.8">
        <div class="fr-tile__body">
          ${description}
        </div>
      </div>
      `;
    return div;
  };
  legend.addTo(map);
}

// Call API to display stats
fetch("/api/stats/geojson/per-prefecture/")
  .then((response) => response.json() as Promise<APIResponse>)
  .then(displayStatsMap);
