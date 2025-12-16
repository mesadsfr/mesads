import * as L from "leaflet";

const map = L.map("map_vehicules_relais", { zoomControl: false }).setView(
  [46.2276, 2.2137],
  6
);

type APIProps = {
  code_insee: string;
  nom: string;
  vehicules_relais_count: number;
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
    const title = props
      ? `${props.nom} (${props.code_insee})`
      : `Nombre de taxis relais`;
    const content = props
      ? this.getInfoboxContent(props.vehicules_relais_count)
      : `Survolez un département pour <br/>afficher le nombre de taxis relais enregistrés`;
    this._div.innerHTML = `
          <div class="fr-tile fr-enlarge-link fr-tile--horizontal" style="opacity: 0.8">
            <div class="fr-tile__body">
                <h4 class="fr-tile__title">${title}</h4>
                <p class="fr-tile__desc">${content}</p>
            </div>
        </div>
        `;
  };

  getInfoboxContent = (vehicules_relais_count: number) => {
    return `${vehicules_relais_count} taxis relais ${
      vehicules_relais_count > 1 ? "enregistrés" : "enregistré"
    }`;
  };
}

function displayStatsMap(data: APIResponse) {
  const info = new InfoBox().addTo(map);

  const geojson = L.geoJSON(data, {
    onEachFeature: (feature, layer: L.GeoJSON) => {
      const center = layer.getBounds().getCenter();

      if (feature.properties.vehicules_relais_count !== 0) {
        const label = L.divIcon({
          className: "vehicule-count-label",
          html: `
        <div style="
          display: flex;
          justify-content: center;
          background-color: #000066;
          align-items: center;
          width: 30px;
          height: 30px;
          border-radius: 50%;
          color: white;
        ">
          ${feature.properties.vehicules_relais_count}
        </div>
      `,
        });
        L.marker(center, { icon: label }).addTo(map);
      }

      layer.on({
        mouseover: () => {
          layer.setStyle({
            fillOpacity: 0.4,
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
        },
      });
    },
  }).addTo(map);
}

// Call API to display stats
fetch("/api/stats/geojson/per-prefecture/")
  .then((response) => response.json() as Promise<APIResponse>)
  .then(displayStatsMap);
