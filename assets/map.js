// Fit a map figure to layout.meta.bounds ([west, south, east, north]) for the size of its graph:
// centre and zoom are computed in the browser, so phones and desktops both see every airport.
window.dash_clientside = Object.assign({}, window.dash_clientside, {
  overview: {
    fitMap: function (figure, graphId) {
      if (!figure || !figure.layout || !figure.layout.meta) {
        return window.dash_clientside.no_update;
      }
      const [boundsWest, south, east, north] = figure.layout.meta.bounds;
      const pad = 1.5; // degrees around the outermost airports
      const west = boundsWest - 5; // extra room in the west for the Lisbon, Porto and Faro labels
      const graph = document.getElementById(graphId);
      const margin = figure.layout.margin || {};
      const width = (graph ? graph.clientWidth : 900) - (margin.l || 0) - (margin.r || 0);
      const height = figure.layout.height - (margin.t || 0) - (margin.b || 0);
      const mercator = (lat) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
      const y1 = mercator(south - pad);
      const y2 = mercator(north + pad);
      const tile = 512; // MapLibre tile size in pixels
      const zoomX = Math.log2((width * 360) / (tile * (east - west + 2 * pad)));
      const zoomY = Math.log2((height * 2 * Math.PI) / (tile * (y2 - y1)));
      const centreY = (y1 + y2) / 2;
      const map = Object.assign({}, figure.layout.map, {
        zoom: Math.min(zoomX, zoomY),
        center: {
          lon: (west + east) / 2,
          lat: ((2 * Math.atan(Math.exp(centreY)) - Math.PI / 2) * 180) / Math.PI,
        },
      });
      return Object.assign({}, figure, { layout: Object.assign({}, figure.layout, { map: map }) });
    },
  },
});
