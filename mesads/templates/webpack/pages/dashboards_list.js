var map = L.map("map", { zoomControl: false }).setView([46.2276, 2.2137], 6);

// Add credits to map
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution:
    '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);

function displayStatsMap(data) {
  const unknown_color = "#0000FF";

  const colors = {
    0: "#A0A0A0",
    1: "#FF0000",
    30: "#FFA500",
    70: "#00FF00",
  };

  const getFillColor = (ads_count, expected_ads_count) => {
    if (expected_ads_count === null) {
      if (ads_count) {
        return unknown_color;
      } else {
        return colors[0];
      }
    }

    const pct_filled = (ads_count / (expected_ads_count || 0)) * 100;

    const rsorted = Object.keys(colors)
      .sort((a, b) => a - b)
      .reverse();
    const key = rsorted.find((e) => pct_filled - e >= 0);
    return colors[key];
  };

  /* Info box on the top right */
  const info = L.control({ position: "topright" });

  info.onAdd = () => {
    this._div = L.DomUtil.create("div", "leaflet-info");
    info.update();
    return this._div;
  };

  getInfoboxContent = (ads_count, expected_ads_count) => {
    const infos = [
      `${ads_count} ADS ${ads_count > 1 ? "enregistrées" : "enregistrée"}`,
    ];

    if (expected_ads_count !== null) {
      infos.push(`${expected_ads_count} ADS au total dans la préfecture`);
      infos.push(
        `<strong>Taux de remplissage: ${Math.round(
          (ads_count / expected_ads_count) * 100
        )}%</strong>`
      );
    } else {
      infos.push("Nombre d'ADS total inconnu pour cette préfecture");
    }

    return infos.join("<br />");
  };

  info.update = (props) => {
    const title = props
      ? `Nombre d'ADS pour ${props.code_insee} - ${props.nom}`
      : `Nombre d'ADS`;

    const content = props
      ? getInfoboxContent(props.ads_count, props.expected_ads_count)
      : `Survolez une région pour afficher les détails`;
    this._div.innerHTML = `
      <div class="fr-tile fr-enlarge-link fr-tile--horizontal">
        <div class="fr-tile__body">
            <h4 class="fr-tile__title">${title}</h4>
            <p class="fr-tile__desc">${content}</p>
        </div>
    </div>
    `;
  };

  info.addTo(map);

  const geojson = L.geoJSON(data, {
    style: (feature) => {
      return {
        fillColor: getFillColor(
          feature.properties.ads_count,
          feature.properties.expected_ads_count
        ),
        fillOpacity: 0.5,
        color: "#777",
        weight: 1,
      };
    },
    onEachFeature: (feature, layer) => {
      layer.on({
        mouseover: () => {
          layer.setStyle({
            fillOpacity: 1,
          });
          info.update(feature.properties);
        },

        mouseout: (e) => {
          geojson.resetStyle(e.target);
          info.update();
        },

        click: () => {
          map.fitBounds(layer.getBounds());
          info.update(feature.properties);
          window.location.href = `#prefecture_${feature.properties.code_insee}`;
        },
      });
    },
  }).addTo(map);

  const legend = L.control({ position: "bottomright" });

  legend.onAdd = () => {
    const div = L.DomUtil.create("div");
    const grades = Object.keys(colors).sort((a, b) => a - b);

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
            <i class="fr-mr-3v" style="background:${
              colors[grades[i]]
            }; width: 24px; height: 24px;"></i>
            ${label}
          </li>
        `;
    }
    description += "</ul>";

    div.innerHTML = `
    <div class="fr-tile fr-enlarge-link fr-tile--horizontal">
      <div class="fr-tile__body">
          <h4 class="fr-tile__title">Légende</h4>
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
  .then((response) => response.json())
  .then(displayStatsMap);
