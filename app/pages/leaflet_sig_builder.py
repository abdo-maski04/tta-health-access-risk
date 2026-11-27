"""Générateur de l'application SIG Web Leaflet Pro pour la Carte 3 de GeoVulnera TTA."""

import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HILLSHADE_PNG = ROOT / "data" / "processed" / "terrain" / "tta_hillshade_display.png"

def generate_leaflet_sig_html(
    routes_geojson: dict,
    hospitals_geojson: dict,
    communes_geojson: dict,
    hydro_rivers_geojson: dict,
    hydro_basins_geojson: dict,
    hazards_geojson: dict,
    isochrones_geojson: dict,
    terrain_bounds: list,
    height: int = 780
) -> str:
    """Génère le code HTML/CSS/JavaScript autonome pour la carte SIG professionnelle."""

    # Serialisation propre JSON pour injection dans le JS
    s_routes = json.dumps(routes_geojson)
    s_hospitals = json.dumps(hospitals_geojson)
    s_communes = json.dumps(communes_geojson)
    s_rivers = json.dumps(hydro_rivers_geojson)
    s_basins = json.dumps(hydro_basins_geojson)
    s_hazards = json.dumps(hazards_geojson)
    s_isochrones = json.dumps(isochrones_geojson)
    s_bounds = json.dumps(terrain_bounds)

    # Conversion de l'image de relief en base64 pour affichage offline direct et fiable dans l'iframe
    hillshade_b64 = ""
    if HILLSHADE_PNG.exists():
        try:
            with open(HILLSHADE_PNG, "rb") as f:
                hillshade_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
        except Exception:
            hillshade_b64 = ""
    s_hillshade = json.dumps(hillshade_b64)

    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>GeoVulnera TTA — SIG Accessibilité Hospitalière</title>
    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="" />
    <!-- Leaflet JS -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        html, body {{ height: 100%; width: 100%; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0f172a; overflow: hidden; }}
        #map-container {{ position: relative; width: 100%; height: {height}px; }}
        #map {{ width: 100%; height: 100%; z-index: 1; }}

        /* Panneau flottant vertical droit */
        #sig-panel {{
            position: absolute;
            top: 14px;
            right: 14px;
            bottom: 14px;
            width: 350px;
            max-width: calc(100vw - 28px);
            background: rgba(255, 255, 255, 0.96);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.22), 0 1px 3px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(226, 232, 240, 0.85);
            z-index: 1000;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        #sig-panel.collapsed {{
            transform: translateX(calc(100% + 20px));
        }}
        #panel-toggle-btn {{
            position: absolute;
            top: 14px;
            right: 14px;
            z-index: 999;
            background: #0284c7;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 8px 14px;
            font-size: 13px;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(2, 132, 199, 0.35);
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        #panel-toggle-btn:hover {{ background: #0369a1; }}

        .panel-header {{
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #ffffff;
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        }}
        .panel-header h3 {{ font-size: 14px; font-weight: 800; letter-spacing: -0.01em; display: flex; align-items: center; gap: 8px; }}
        .panel-close-btn {{ background: transparent; border: none; color: #94a3b8; font-size: 18px; cursor: pointer; padding: 2px 6px; border-radius: 4px; }}
        .panel-close-btn:hover {{ color: #ffffff; background: rgba(255,255,255,0.1); }}

        .panel-body {{
            padding: 10px 14px;
            overflow-y: auto;
            flex: 1;
            font-size: 12px;
            color: #334155;
        }}

        /* Accordéon repliable */
        .sig-accordion {{ border-bottom: 1px solid #e2e8f0; margin-bottom: 8px; }}
        .sig-acc-btn {{
            width: 100%;
            text-align: left;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 9px 12px;
            font-size: 12px;
            font-weight: 700;
            color: #1e293b;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }}
        .sig-acc-btn:hover {{ background: #f1f5f9; }}
        .sig-acc-content {{ padding: 6px 4px 10px; display: block; }}
        .sig-acc-content.hidden {{ display: none; }}

        /* Filtres */
        .filter-group {{ margin-bottom: 8px; }}
        .filter-label {{ font-size: 11px; font-weight: 600; color: #475569; margin-bottom: 3px; display: block; }}
        .filter-select {{
            width: 100%;
            padding: 6px 10px;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            font-size: 11px;
            background: #ffffff;
            color: #0f172a;
            outline: none;
        }}
        .filter-select:focus {{ border-color: #0284c7; box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.15); }}

        /* Couches switchers */
        .layer-switch {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px dotted #e2e8f0;
        }}
        .layer-switch-label {{ display: flex; align-items: center; gap: 8px; font-size: 11.5px; color: #1e293b; }}
        .toggle-chk {{ cursor: pointer; width: 16px; height: 16px; accent-color: #0284c7; }}

        /* Légende */
        .legend-item {{ display: flex; align-items: center; gap: 8px; margin-bottom: 5px; font-size: 11px; }}
        .legend-box {{ width: 18px; height: 6px; border-radius: 2px; flex-shrink: 0; }}
        .legend-icon {{ width: 14px; height: 14px; flex-shrink: 0; display: inline-flex; align-items: center; justify-content: center; }}

        /* Basemap options */
        .basemap-opt {{ display: flex; align-items: center; gap: 8px; padding: 5px 0; cursor: pointer; font-size: 11.5px; }}

        /* Popups professionnelles Leaflet sans template défaillant */
        .leaflet-popup-content-wrapper {{
            border-radius: 10px !important;
            padding: 0 !important;
            overflow: hidden !important;
            box-shadow: 0 10px 25px rgba(0,0,0,0.25) !important;
            border: 1px solid #cbd5e1 !important;
        }}
        .leaflet-popup-content {{ margin: 0 !important; line-height: 1.4 !important; min-width: 260px !important; }}
        .popup-card {{ background: #ffffff; color: #1e293b; font-family: inherit; }}
        .popup-head {{ background: #0f172a; color: #ffffff; padding: 10px 14px; border-bottom: 2px solid #0284c7; }}
        .popup-head h4 {{ font-size: 14px; font-weight: 800; margin: 0; color: #38bdf8; }}
        .popup-head .sub {{ font-size: 11px; color: #94a3b8; margin-top: 2px; }}
        .popup-body {{ padding: 12px 14px; font-size: 11.5px; }}
        .popup-row {{ display: flex; justify-content: space-between; margin-bottom: 5px; border-bottom: 1px dotted #f1f5f9; padding-bottom: 3px; }}
        .popup-row .lbl {{ color: #64748b; font-weight: 500; }}
        .popup-row .val {{ font-weight: 700; color: #0f172a; text-align: right; }}
        .popup-badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 700;
            margin-top: 6px;
        }}

        /* Contrôles cartographiques en haut à gauche */
        .leaflet-top.leaflet-left {{ margin-top: 10px; margin-left: 10px; }}
        .map-ctrl-btn {{
            background: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 6px rgba(0,0,0,0.12);
            cursor: pointer;
            margin-bottom: 6px;
            font-weight: 700;
            color: #334155;
        }}
        .map-ctrl-btn:hover {{ background: #f8fafc; color: #0284c7; }}
    </style>
</head>
<body>
    <div id="map-container">
        <div id="map"></div>

        <!-- Bouton réouverture du panneau si replié -->
        <button id="panel-toggle-btn" style="display:none;" onclick="togglePanel(true)">
            <span>🧭</span> Panneau SIG
        </button>

        <!-- Panneau flottant vertical droit -->
        <div id="sig-panel">
            <div class="panel-header">
                <h3><span>🗺️</span> Exploration SIG TTA</h3>
                <button class="panel-close-btn" onclick="togglePanel(false)" title="Replier le panneau">✕</button>
            </div>
            <div class="panel-body">

                <!-- Section A : Filtres Géographiques -->
                <div class="sig-accordion">
                    <button class="sig-acc-btn" onclick="toggleAcc(this)">
                        <span>🔍 A. Filtres Géographiques</span>
                        <span class="acc-arrow">▼</span>
                    </button>
                    <div class="sig-acc-content">
                        <div class="filter-group">
                            <label class="filter-label">Province / Préfecture :</label>
                            <select id="flt-province" class="filter-select" onchange="applyFilters()">
                                <option value="">Toutes les provinces (8)</option>
                            </select>
                        </div>
                        <div class="filter-group">
                            <label class="filter-label">Focus sur une commune :</label>
                            <select id="flt-commune" class="filter-select" onchange="applyCommuneFocus()">
                                <option value="">Toutes les communes (146)</option>
                            </select>
                        </div>
                        <div class="filter-group">
                            <label class="filter-label">Hôpital de destination :</label>
                            <select id="flt-hospital" class="filter-select" onchange="applyFilters()">
                                <option value="">Tous les hôpitaux</option>
                            </select>
                        </div>
                        <div class="filter-group">
                            <label class="filter-label">Classe d'accès clinique :</label>
                            <select id="flt-duration" class="filter-select" onchange="applyFilters()">
                                <option value="">Toutes les classes</option>
                                <option value="15">≤ 15 min (Très rapide)</option>
                                <option value="30">15–30 min (Bonne accessibilité)</option>
                                <option value="45">30–45 min (Intermédiaire)</option>
                                <option value="60">45–60 min (Limitée)</option>
                                <option value="999">> 60 min (Critique / Éloignée)</option>
                            </select>
                        </div>
                        <div class="filter-group">
                            <label class="filter-label">Provenance de l'itinéraire :</label>
                            <select id="flt-provenance" class="filter-select" onchange="applyFilters()">
                                <option value="">Tous les statuts</option>
                                <option value="recalc">Recalculé ORS v2 (50)</option>
                                <option value="prot">Historique préservé v1 (96)</option>
                            </select>
                        </div>
                    </div>
                </div>

                <!-- Section B : Couches Cartographiques -->
                <div class="sig-accordion">
                    <button class="sig-acc-btn" onclick="toggleAcc(this)">
                        <span>🗂️ B. Couches Cartographiques</span>
                        <span class="acc-arrow">▼</span>
                    </button>
                    <div class="sig-acc-content">
                        <div class="layer-switch">
                            <span class="layer-switch-label">🛣️ Itinéraires routiers</span>
                            <input type="checkbox" id="chk-routes" class="toggle-chk" checked onchange="toggleLayer('routes')" />
                        </div>
                        <div class="layer-switch">
                            <span class="layer-switch-label">🗺️ Limites communales</span>
                            <input type="checkbox" id="chk-communes" class="toggle-chk" checked onchange="toggleLayer('communes')" />
                        </div>
                        <div class="layer-switch">
                            <span class="layer-switch-label">🏥 Hôpitaux publics (SVG)</span>
                            <input type="checkbox" id="chk-hospitals" class="toggle-chk" checked onchange="toggleLayer('hospitals')" />
                        </div>
                        <div class="layer-switch">
                            <span class="layer-switch-label">📍 Chefs-lieux communaux</span>
                            <input type="checkbox" id="chk-origins" class="toggle-chk" onchange="toggleLayer('origins')" />
                        </div>
                        <div class="layer-switch">
                            <span class="layer-switch-label">🏔️ Relief & Ombrage (MNT)</span>
                            <input type="checkbox" id="chk-terrain" class="toggle-chk" checked onchange="toggleLayer('terrain')" />
                        </div>
                        <div class="layer-switch">
                            <span class="layer-switch-label">🌊 Réseau hydrographique & Oueds</span>
                            <input type="checkbox" id="chk-hydro" class="toggle-chk" checked onchange="toggleLayer('hydro')" />
                        </div>
                        <div class="layer-switch">
                            <span class="layer-switch-label">⚠️ Contraintes morpho-topographiques</span>
                            <input type="checkbox" id="chk-hazards" class="toggle-chk" onchange="toggleLayer('hazards')" />
                        </div>
                        <div class="layer-switch">
                            <span class="layer-switch-label">⏱️ Zones estimées d'accessibilité</span>
                            <input type="checkbox" id="chk-isochrones" class="toggle-chk" onchange="toggleLayer('isochrones')" />
                        </div>
                    </div>
                </div>

                <!-- Section C : Légende Cartographique Dynamique -->
                <div class="sig-accordion">
                    <button class="sig-acc-btn" onclick="toggleAcc(this)">
                        <span>🎨 C. Légende Dynamique</span>
                        <span class="acc-arrow">▼</span>
                    </button>
                    <div class="sig-acc-content" id="legend-content">
                        <!-- Généré dynamiquement en JS selon les couches actives -->
                    </div>
                </div>

                <!-- Section D : Fond Cartographique -->
                <div class="sig-accordion">
                    <button class="sig-acc-btn" onclick="toggleAcc(this)">
                        <span>🌐 D. Fond Cartographique</span>
                        <span class="acc-arrow">▼</span>
                    </button>
                    <div class="sig-acc-content">
                        <label class="basemap-opt">
                            <input type="radio" name="basemap" value="esri_gray" checked onchange="changeBasemap('esri_gray')" />
                            <span>1. Carte claire (Esri Light Gray)</span>
                        </label>
                        <label class="basemap-opt">
                            <input type="radio" name="basemap" value="osm" onchange="changeBasemap('osm')" />
                            <span>2. OpenStreetMap (Standard)</span>
                        </label>
                        <label class="basemap-opt">
                            <input type="radio" name="basemap" value="esri_topo" onchange="changeBasemap('esri_topo')" />
                            <span>3. Topographique (Esri World Topo)</span>
                        </label>
                        <label class="basemap-opt">
                            <input type="radio" name="basemap" value="esri_sat" onchange="changeBasemap('esri_sat')" />
                            <span>4. Image satellite (Esri World Imagery)</span>
                        </label>
                        <label class="basemap-opt">
                            <input type="radio" name="basemap" value="esri_hybrid" onchange="changeBasemap('esri_hybrid')" />
                            <span>5. Satellite Hybride (Repères & Noms)</span>
                        </label>
                    </div>
                </div>

            </div>
        </div>
    </div>

    <!-- Script de logique SIG Leaflet -->
    <script>
        // Données injectées
        const routesData = {s_routes};
        const hospitalsData = {s_hospitals};
        const communesData = {s_communes};
        const riversData = {s_rivers};
        const basinsData = {s_basins};
        const hazardsData = {s_hazards};
        const isochronesData = {s_isochrones};
        const terrainBounds = {s_bounds}; // [west, south, east, north]
        const hillshadeB64 = {s_hillshade};

        // 1. Initialisation carte Leaflet
        const map = L.map('map', {{
            center: [35.35, -5.35],
            zoom: 8,
            minZoom: 7,
            maxZoom: 18,
            zoomControl: false
        }});

        // Invalidation dimensionnelle différée pour garantir le rendu complet dans iframe Streamlit
        setTimeout(function() {{ map.invalidateSize(); }}, 200);
        setTimeout(function() {{ map.invalidateSize(); }}, 800);
        window.addEventListener('resize', function() {{ map.invalidateSize(); }});

        // Contrôles personnalisés
        L.control.zoom({{ position: 'topleft' }}).addTo(map);
        L.control.scale({{ position: 'bottomleft', metric: true, imperial: false }}).addTo(map);

        // Bouton Recenter
        const recenterBtn = L.control({{ position: 'topleft' }});
        recenterBtn.onAdd = function() {{
            const div = L.DomUtil.create('div', 'map-ctrl-btn');
            div.innerHTML = '⟲';
            div.title = 'Recentrer sur la région TTA';
            div.onclick = function() {{ map.setView([35.35, -5.35], 8); }};
            return div;
        }};
        recenterBtn.addTo(map);

        // 2. Définition des fonds cartographiques mondiaux fiables et certifiés sans clé API
        const basemaps = {{
            esri_gray: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
                maxZoom: 16
            }}),
            osm: L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '&copy; OpenStreetMap contributors',
                maxZoom: 19
            }}),
            esri_topo: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                attribution: 'Tiles &copy; Esri',
                maxZoom: 19
            }}),
            esri_sat: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                attribution: 'Tiles &copy; Esri',
                maxZoom: 19
            }}),
            esri_hybrid: L.layerGroup([
                L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{ maxZoom: 19 }}),
                L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                    attribution: 'Tiles &copy; Esri',
                    maxZoom: 19
                }})
            ])
        }};
        let currentBasemap = basemaps.esri_gray.addTo(map);

        function changeBasemap(key) {{
            map.removeLayer(currentBasemap);
            currentBasemap = basemaps[key];
            currentBasemap.addTo(map);
        }}

        // 3. Définition des Symboles SVG Vectoriels Professionnels pour Hôpitaux (sans emojis)
        function getHospitalSvgIcon(category) {{
            let fill = '#dc2626';
            let shape = '';
            const sz = 28;
            if (category === 'CHU') {{
                fill = '#b91c1c'; // Rouge profond
                // Losange avec croix blanche
                shape = `<polygon points="14,2 26,14 14,26 2,14" fill="${{fill}}" stroke="#ffffff" stroke-width="2"/>
                         <path d="M14,8 L14,20 M8,14 L20,14" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round"/>`;
            }} else if (category === 'CHR') {{
                fill = '#1d4ed8'; // Bleu roi
                // Carré avec croix
                shape = `<rect x="3" y="3" width="22" height="22" rx="4" fill="${{fill}}" stroke="#ffffff" stroke-width="2"/>
                         <path d="M14,7 L14,21 M7,14 L21,14" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round"/>`;
            }} else if (category === 'HR') {{
                fill = '#0284c7'; // Bleu ciel soutenu
                // Carré arrondi
                shape = `<rect x="3" y="3" width="22" height="22" rx="4" fill="${{fill}}" stroke="#ffffff" stroke-width="2"/>
                         <path d="M14,8 L14,20 M8,14 L20,14" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round"/>`;
            }} else if (category === 'CHP') {{
                fill = '#2563eb'; // Bleu provincial
                // Cercle avec croix
                shape = `<circle cx="14" cy="14" r="11" fill="${{fill}}" stroke="#ffffff" stroke-width="2"/>
                         <path d="M14,8 L14,20 M8,14 L20,14" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round"/>`;
            }} else {{
                // HPr (Hôpital de proximité)
                fill = '#7c3aed'; // Violet
                // Hexagone
                shape = `<polygon points="14,3 24,8 24,20 14,25 4,20 4,8" fill="${{fill}}" stroke="#ffffff" stroke-width="2"/>
                         <path d="M14,8 L14,20 M8,14 L20,14" stroke="#ffffff" stroke-width="2" stroke-linecap="round"/>`;
            }}
            const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${{sz}}" height="${{sz}}" viewBox="0 0 28 28">${{shape}}</svg>`;
            return L.divIcon({{
                html: svg,
                className: 'sig-hosp-icon',
                iconSize: [sz, sz],
                iconAnchor: [sz/2, sz/2],
                popupAnchor: [0, -sz/2]
            }});
        }}

        // 4. Groupes de Couches (LayerGroups)
        const layers = {{
            terrain: L.layerGroup(),
            isochrones: L.layerGroup(),
            hazards: L.layerGroup(),
            basins: L.layerGroup(),
            hydro: L.layerGroup(),
            communes: L.layerGroup(),
            routes: L.layerGroup(),
            hospitals: L.layerGroup(),
            origins: L.layerGroup()
        }};

        // Couche Terrain Image Overlay
        if (terrainBounds && terrainBounds.length === 4 && hillshadeB64) {{
            // bounds: [west, south, east, north] -> Leaflet expects [[south, west], [north, east]]
            const imgBounds = [[terrainBounds[1], terrainBounds[0]], [terrainBounds[3], terrainBounds[2]]];
            const terrainOverlay = L.imageOverlay(hillshadeB64, imgBounds, {{
                opacity: 0.65,
                interactive: false
            }});
            layers.terrain.addLayer(terrainOverlay);
        }}

        // Couche Bassins Versants
        if (basinsData && basinsData.features) {{
            L.geoJSON(basinsData, {{
                style: {{
                    color: '#0284c7',
                    weight: 1.2,
                    dashArray: '4, 4',
                    fillColor: '#0284c7',
                    fillOpacity: 0.04
                }}
            }}).addTo(layers.basins);
        }}

        // Couche Oueds et Hydrographie
        if (riversData && riversData.features) {{
            L.geoJSON(riversData, {{
                style: function(feat) {{
                    const ord = feat.properties.RIV_ORD || 3;
                    return {{
                        color: ord <= 2 ? '#0284c7' : '#38bdf8',
                        weight: ord <= 2 ? 3.5 : 2.0,
                        opacity: 0.85
                    }};
                }},
                onEachFeature: function(feat, layer) {{
                    const p = feat.properties;
                    const nom = p.name || 'Oued régional';
                    const cat = p.category || "Cours d'eau";
                    const ord = p.RIV_ORD || 'Non renseigné';
                    const len = p.LENGTH_KM ? p.LENGTH_KM + ' km' : 'Non renseigné';
                    layer.bindTooltip(`<b>${{nom}}</b> (${{cat}})`, {{ sticky: true }});
                    layer.bindPopup(`
                        <div class="popup-card">
                            <div class="popup-head" style="background:#0369a1;">
                                <h4>🌊 ${{nom}}</h4>
                                <div class="sub">${{cat}}</div>
                            </div>
                            <div class="popup-body">
                                <div class="popup-row"><span class="lbl">Ordre de Strahler :</span><span class="val">${{ord}}</span></div>
                                <div class="popup-row"><span class="lbl">Longueur estimée :</span><span class="val">${{len}}</span></div>
                                <div class="popup-row"><span class="lbl">Source :</span><span class="val">HydroRIVERS / ABHL</span></div>
                            </div>
                        </div>
                    `);
                }}
            }}).addTo(layers.hydro);
        }}

        // Couche Aléas & Contraintes ABHL
        if (hazardsData && hazardsData.features) {{
            L.geoJSON(hazardsData, {{
                style: function(feat) {{
                    const p = feat.properties;
                    const isFlood = (p.type_alea || '').includes('Inondation');
                    return {{
                        color: isFlood ? '#0284c7' : '#ea580c',
                        weight: 2,
                        fillColor: isFlood ? '#0284c7' : '#ea580c',
                        fillOpacity: 0.28
                    }};
                }},
                onEachFeature: function(feat, layer) {{
                    const p = feat.properties;
                    const nom = p.nom || 'Zone de vigilance';
                    const alea = p.type_alea || 'Contrainte morpho-topographique';
                    const niv = p.niveau || 'Vigilance institutionnelle';
                    const src = p.organisme_source || 'ABHL Loukkos';
                    const prov = p.province || 'Région TTA';
                    layer.bindTooltip(`<b>${{nom}}</b> — ${{alea}}`, {{ sticky: true }});
                    layer.bindPopup(`
                        <div class="popup-card">
                            <div class="popup-head" style="background:#ea580c;">
                                <h4>⚠️ ${{nom}}</h4>
                                <div class="sub">${{alea}}</div>
                            </div>
                            <div class="popup-body">
                                <div class="popup-row"><span class="lbl">Niveau de vigilance :</span><span class="val">${{niv}}</span></div>
                                <div class="popup-row"><span class="lbl">Province :</span><span class="val">${{prov}}</span></div>
                                <div class="popup-row"><span class="lbl">Source institutionnelle :</span><span class="val">${{src}}</span></div>
                            </div>
                        </div>
                    `);
                }}
            }}).addTo(layers.hazards);
        }}

        // Couche Zones Estimées d'Accessibilité (Isochrones)
        if (isochronesData && isochronesData.features) {{
            const isoColors = {{
                15: '#047857',
                30: '#0d9488',
                45: '#eab308',
                60: '#f97316'
            }};
            L.geoJSON(isochronesData, {{
                style: function(feat) {{
                    const m = feat.properties.isochrone_min || 60;
                    return {{
                        color: isoColors[m] || '#dc2626',
                        weight: 2,
                        fillColor: isoColors[m] || '#dc2626',
                        fillOpacity: 0.22
                    }};
                }},
                onEachFeature: function(feat, layer) {{
                    const p = feat.properties;
                    const seuil = p.isochrone_min || '60';
                    const pop = p.population_couverte ? Number(p.population_couverte).toLocaleString('fr-FR') + ' hab.' : 'Non renseigné';
                    const pct = p.pct_population_regionale ? p.pct_population_regionale + ' %' : '';
                    const comCount = p.nb_communes_couvertes || 'Non renseigné';
                    const cat = p.threshold_category || 'Accessibilité hospitalière';
                    layer.bindTooltip(`<b>Accès ≤ ${{seuil}} min</b> (${{pop}})`, {{ sticky: true }});
                    layer.bindPopup(`
                        <div class="popup-card">
                            <div class="popup-head" style="background:#047857;">
                                <h4>⏱️ Seuil d'Accès Hospitalier ≤ ${{seuil}} min</h4>
                                <div class="sub">${{cat}}</div>
                            </div>
                            <div class="popup-body">
                                <div class="popup-row"><span class="lbl">Communes couvertes :</span><span class="val">${{comCount}} / 146</span></div>
                                <div class="popup-row"><span class="lbl">Population couverte :</span><span class="val">${{pop}} (${{pct}})</span></div>
                                <div class="popup-row"><span class="lbl">Méthode de calcul :</span><span class="val">Modèle empirique communal</span></div>
                                <div style="margin-top:8px; font-size:10px; color:#64748b; background:#f8fafc; padding:6px; border-radius:4px; border:1px solid #e2e8f0;">
                                    <b>Note méthodologique :</b> Ce tracé représente l'enveloppe territoriale des chefs-lieux communaux dont le trajet routier ORS respecte ce seuil, et non un isochrone continu au mètre près.
                                </div>
                            </div>
                        </div>
                    `);
                }}
            }}).addTo(layers.isochrones);
        }}

        // Couche Communes (Polygones)
        let communeLayersByCode = {{}};
        if (communesData && communesData.features) {{
            L.geoJSON(communesData, {{
                style: function(feat) {{
                    const t = feat.properties.temps_min || 0;
                    let c = '#dc2626';
                    if (t <= 15) c = '#047857';
                    else if (t <= 30) c = '#0d9488';
                    else if (t <= 45) c = '#eab308';
                    else if (t <= 60) c = '#f97316';
                    return {{
                        color: '#475569',
                        weight: 1,
                        fillColor: c,
                        fillOpacity: 0.35
                    }};
                }},
                onEachFeature: function(feat, layer) {{
                    const p = feat.properties;
                    const code = p.commune_code;
                    communeLayersByCode[code] = layer;

                    const nom = p.name_fr || 'Commune';
                    const prov = p.province || 'Région TTA';
                    const pop = p.population_2024 ? Number(p.population_2024).toLocaleString('fr-FR') + ' hab.' : 'Non disponible';
                    const hosp = p.hospital_canonical || p.hospital_name || 'Hôpital de référence';
                    const t = p.temps_min ? Number(p.temps_min).toFixed(1) + ' min' : 'Non renseigné';
                    const d = p.distance_km ? Number(p.distance_km).toFixed(1) + ' km' : 'Non renseigné';
                    const provType = p.is_recalculated ? 'Recalculé ORS v2' : 'Historique préservé v1';
                    const tier = p.access_tier || 'Standard';

                    layer.bindTooltip(`<b>${{nom}}</b> (${{prov}})<br/>Accès : <b>${{t}}</b> (${{d}})`, {{ sticky: true }});
                    layer.bindPopup(`
                        <div class="popup-card">
                            <div class="popup-head">
                                <h4>📍 ${{nom}}</h4>
                                <div class="sub">${{prov}} · Code HCP : ${{code}}</div>
                            </div>
                            <div class="popup-body">
                                <div class="popup-row"><span class="lbl">Population légale 2024 :</span><span class="val">${{pop}}</span></div>
                                <div class="popup-row"><span class="lbl">Hôpital de destination :</span><span class="val">${{hosp}}</span></div>
                                <div class="popup-row"><span class="lbl">Temps de trajet routier :</span><span class="val" style="color:#d97706; font-size:12.5px;">${{t}}</span></div>
                                <div class="popup-row"><span class="lbl">Distance routière :</span><span class="val">${{d}}</span></div>
                                <div class="popup-row"><span class="lbl">Palier d'urgence :</span><span class="val">${{tier}}</span></div>
                                <div class="popup-row"><span class="lbl">Provenance de l'itinéraire :</span><span class="val">${{provType}}</span></div>
                            </div>
                        </div>
                    `);
                }}
            }}).addTo(layers.communes);
        }}

        // Couche Itinéraires Routiers (Lignes)
        let routeLayers = [];
        if (routesData && routesData.features) {{
            L.geoJSON(routesData, {{
                style: function(feat) {{
                    const isRecalc = feat.properties.is_recalculated;
                    return {{
                        color: isRecalc ? '#1d4ed8' : '#059669', // Bleu soutenu pour recalculé v2, vert foncé pour préservé v1
                        weight: 3.5,
                        opacity: 0.85
                    }};
                }},
                onEachFeature: function(feat, layer) {{
                    const p = feat.properties;
                    routeLayers.push({{ layer: layer, properties: p }});
                    const com = p.name_fr || 'Commune';
                    const hosp = p.hospital_canonical || p.hospital_name || 'Hôpital';
                    const t = p.temps_min ? Number(p.temps_min).toFixed(1) + ' min' : 'N/A';
                    const d = p.distance_km ? Number(p.distance_km).toFixed(1) + ' km' : 'N/A';
                    const stat = p.statut_calcul || (p.is_recalculated ? 'Recalculé ORS v2' : 'Historique préservé v1');

                    layer.bindTooltip(`<b>${{com}}</b> ➔ <b>${{hosp}}</b> (${{t}})`, {{ sticky: true }});
                    layer.bindPopup(`
                        <div class="popup-card">
                            <div class="popup-head" style="background:#1e293b;">
                                <h4>🛣️ Itinéraire d'Évacuation</h4>
                                <div class="sub">${{com}} ➔ ${{hosp}}</div>
                            </div>
                            <div class="popup-body">
                                <div class="popup-row"><span class="lbl">Temps de parcours estimé :</span><span class="val" style="color:#2563eb;">${{t}}</span></div>
                                <div class="popup-row"><span class="lbl">Distance routière :</span><span class="val">${{d}}</span></div>
                                <div class="popup-row"><span class="lbl">Vitesse moyenne estimée :</span><span class="val">~${{p.speed_kmh || (Number(d)/Math.max(0.01, Number(t)/60)).toFixed(1)}} km/h</span></div>
                                <div class="popup-row"><span class="lbl">Statut de validation :</span><span class="val">${{stat}}</span></div>
                            </div>
                        </div>
                    `);
                }}
            }}).addTo(layers.routes);
        }}

        // Couche Hôpitaux Publics (Marqueurs SVG Vectoriels Nets)
        if (hospitalsData && hospitalsData.features) {{
            L.geoJSON(hospitalsData, {{
                pointToLayer: function(feat, latlng) {{
                    const cat = feat.properties.category || 'CHP';
                    return L.marker(latlng, {{ icon: getHospitalSvgIcon(cat) }});
                }},
                onEachFeature: function(feat, layer) {{
                    const p = feat.properties;
                    const nom = p.name || 'Hôpital public';
                    const cat = p.category || 'CHP';
                    const catLbl = p.category_label || 'Centre Hospitalier';
                    const prov = p.province || 'Région TTA';
                    const com = p.commune || p.commune_name_official || 'Région TTA';

                    let coords = 'Non renseigné';
                    if (feat.geometry && feat.geometry.coordinates && feat.geometry.coordinates.length >= 2) {{
                        coords = feat.geometry.coordinates[1].toFixed(4) + ', ' + feat.geometry.coordinates[0].toFixed(4);
                    }} else if (layer.getLatLng) {{
                        const ll = layer.getLatLng();
                        coords = ll.lat.toFixed(4) + ', ' + ll.lng.toFixed(4);
                    }}

                    const beds = p.capacity_beds_est ? p.capacity_beds_est + ' lits (Estimation publique non certifiée)' : 'Non certifié dans la base locale';

                    layer.bindTooltip(`<b>${{nom}}</b> [${{cat}}]`, {{ sticky: true }});
                    layer.bindPopup(`
                        <div class="popup-card">
                            <div class="popup-head" style="background:#b91c1c;">
                                <h4>🏥 ${{nom}}</h4>
                                <div class="sub">${{catLbl}} [${{cat}}]</div>
                            </div>
                            <div class="popup-body">
                                <div class="popup-row"><span class="lbl">Catégorie officielle :</span><span class="val">${{cat}}</span></div>
                                <div class="popup-row"><span class="lbl">Province / Préfecture :</span><span class="val">${{prov}}</span></div>
                                <div class="popup-row"><span class="lbl">Commune d'implantation :</span><span class="val">${{com}}</span></div>
                                <div class="popup-row"><span class="lbl">Statut juridique :</span><span class="val">Établissement Public (MSPS)</span></div>
                                <div class="popup-row"><span class="lbl">Capacité indicative :</span><span class="val">${{beds}}</span></div>
                                <div class="popup-row"><span class="lbl">Coordonnées GPS :</span><span class="val">${{coords}}</span></div>
                            </div>
                        </div>
                    `);
                }}
            }}).addTo(layers.hospitals);
        }}

        // Couche Chefs-lieux communaux
        if (routesData && routesData.features) {{
            routesData.features.forEach(function(f) {{
                const p = f.properties;
                if (f.geometry && f.geometry.coordinates && f.geometry.coordinates.length > 0) {{
                    const pt = f.geometry.coordinates[0]; // [lon, lat]
                    const marker = L.circleMarker([pt[1], pt[0]], {{
                        radius: 4,
                        fillColor: '#1e293b',
                        color: '#ffffff',
                        weight: 1.5,
                        fillOpacity: 0.9
                    }});
                    marker.bindTooltip(`Chef-lieu : ${{p.name_fr}}`);
                    layers.origins.addLayer(marker);
                }}
            }});
        }}

        // Activer les couches initiales avec capture d'erreurs
        try {{
            layers.terrain.addTo(map);
            layers.hydro.addTo(map);
            layers.communes.addTo(map);
            layers.routes.addTo(map);
            layers.hospitals.addTo(map);
        }} catch(err) {{
            console.error("Erreur lors de l'activation des couches initiales :", err);
        }}

        // 5. Fonctions d'interaction UI
        function togglePanel(open) {{
            const p = document.getElementById('sig-panel');
            const btn = document.getElementById('panel-toggle-btn');
            if (open) {{
                p.classList.remove('collapsed');
                btn.style.display = 'none';
            }} else {{
                p.classList.add('collapsed');
                btn.style.display = 'flex';
            }}
        }}

        function toggleAcc(btn) {{
            const content = btn.nextElementSibling;
            const arrow = btn.querySelector('.acc-arrow');
            if (content.classList.contains('hidden')) {{
                content.classList.remove('hidden');
                arrow.innerText = '▼';
            }} else {{
                content.classList.add('hidden');
                arrow.innerText = '▶';
            }}
        }}

        function toggleLayer(layerKey) {{
            const chk = document.getElementById('chk-' + layerKey);
            if (chk.checked) {{
                map.addLayer(layers[layerKey]);
            }} else {{
                map.removeLayer(layers[layerKey]);
            }}
            updateLegend();
        }}

        // 6. Remplissage dynamique des filtres
        function populateFilters() {{
            const provSet = new Set();
            const comSelect = document.getElementById('flt-commune');
            const provSelect = document.getElementById('flt-province');
            const hospSelect = document.getElementById('flt-hospital');
            const hospSet = new Set();

            if (routesData && routesData.features) {{
                // Trier par nom
                const sortedFeats = routesData.features.slice().sort((a,b) => (a.properties.name_fr || '').localeCompare(b.properties.name_fr || ''));
                sortedFeats.forEach(f => {{
                    const p = f.properties;
                    if (p.province) provSet.add(p.province);
                    if (p.hospital_canonical) hospSet.add(p.hospital_canonical);

                    const opt = document.createElement('option');
                    opt.value = p.commune_code;
                    opt.innerText = `${{p.name_fr}} (${{p.province}})`;
                    comSelect.appendChild(opt);
                }});

                Array.from(provSet).sort().forEach(pr => {{
                    const opt = document.createElement('option');
                    opt.value = pr;
                    opt.innerText = pr;
                    provSelect.appendChild(opt);
                }});

                Array.from(hospSet).sort().forEach(h => {{
                    const opt = document.createElement('option');
                    opt.value = h;
                    opt.innerText = h;
                    hospSelect.appendChild(opt);
                }});
            }}
        }}
        try {{
            populateFilters();
        }} catch(err) {{
            console.error("Erreur lors de populateFilters :", err);
        }}

        function applyFilters() {{
            const prov = document.getElementById('flt-province').value;
            const hosp = document.getElementById('flt-hospital').value;
            const dur = document.getElementById('flt-duration').value;
            const provType = document.getElementById('flt-provenance').value;

            // Filtrer routes
            routeLayers.forEach(item => {{
                const p = item.properties;
                let show = true;
                if (prov && p.province !== prov) show = false;
                if (hosp && p.hospital_canonical !== hosp) show = false;
                if (provType === 'recalc' && !p.is_recalculated) show = false;
                if (provType === 'prot' && p.is_recalculated) show = false;
                if (dur) {{
                    const t = Number(p.temps_min);
                    if (dur === '15' && t > 15) show = false;
                    else if (dur === '30' && (t <= 15 || t > 30)) show = false;
                    else if (dur === '45' && (t <= 30 || t > 45)) show = false;
                    else if (dur === '60' && (t <= 45 || t > 60)) show = false;
                    else if (dur === '999' && t <= 60) show = false;
                }}

                if (show) {{
                    item.layer.setStyle({{ opacity: 0.85, weight: 3.5 }});
                }} else {{
                    item.layer.setStyle({{ opacity: 0, weight: 0 }});
                }}
            }});
        }}

        function applyCommuneFocus() {{
            const code = document.getElementById('flt-commune').value;
            if (!code) {{
                map.setView([35.35, -5.35], 8);
                return;
            }}
            const layer = communeLayersByCode[code];
            if (layer) {{
                map.fitBounds(layer.getBounds(), {{ padding: [60, 60], maxZoom: 12 }});
                layer.openPopup();
            }}
        }}

        // 7. Légende Cartographique Dynamique
        function updateLegend() {{
            const container = document.getElementById('legend-content');
            let html = '';

            const chkRoutes = document.getElementById('chk-routes').checked;
            const chkHosp = document.getElementById('chk-hospitals').checked;
            const chkHydro = document.getElementById('chk-hydro').checked;
            const chkHazards = document.getElementById('chk-hazards').checked;
            const chkIso = document.getElementById('chk-isochrones').checked;
            const chkCommunes = document.getElementById('chk-communes').checked;

            if (chkRoutes) {{
                html += `
                    <div style="font-weight:700; color:#0f172a; margin:4px 0 6px;">Itinéraires routiers :</div>
                    <div class="legend-item"><span class="legend-box" style="background:#1d4ed8; height:4px;"></span> <span>Recalculé ORS v2 (50)</span></div>
                    <div class="legend-item"><span class="legend-box" style="background:#059669; height:4px;"></span> <span>Historique préservé v1 (96)</span></div>
                `;
            }}

            if (chkHosp) {{
                html += `
                    <div style="font-weight:700; color:#0f172a; margin:8px 0 6px;">Hôpitaux publics (SVG) :</div>
                    <div class="legend-item"><span class="legend-icon"><svg width="14" height="14" viewBox="0 0 28 28"><polygon points="14,2 26,14 14,26 2,14" fill="#b91c1c"/><path d="M14,8 L14,20 M8,14 L20,14" stroke="#fff" stroke-width="3"/></svg></span> <span>CHU Tertiaire (Tanger)</span></div>
                    <div class="legend-item"><span class="legend-icon"><svg width="14" height="14" viewBox="0 0 28 28"><rect x="3" y="3" width="22" height="22" rx="4" fill="#1d4ed8"/><path d="M14,7 L14,21 M7,14 L21,14" stroke="#fff" stroke-width="3"/></svg></span> <span>CHR Secondaire (Tétouan)</span></div>
                    <div class="legend-item"><span class="legend-icon"><svg width="14" height="14" viewBox="0 0 28 28"><circle cx="14" cy="14" r="11" fill="#2563eb"/><path d="M14,8 L14,20 M8,14 L20,14" stroke="#fff" stroke-width="3"/></svg></span> <span>CHP Provincial (8 hôpitaux)</span></div>
                    <div class="legend-item"><span class="legend-icon"><svg width="14" height="14" viewBox="0 0 28 28"><polygon points="14,3 24,8 24,20 14,25 4,20 4,8" fill="#7c3aed"/><path d="M14,8 L14,20 M8,14 L20,14" stroke="#fff" stroke-width="3"/></svg></span> <span>HPr Proximité (4 hôpitaux)</span></div>
                `;
            }}

            if (chkCommunes) {{
                html += `
                    <div style="font-weight:700; color:#0f172a; margin:8px 0 6px;">Classes d'accès communal :</div>
                    <div class="legend-item"><span class="legend-box" style="background:#047857;"></span> <span>≤ 15 min (Très rapide)</span></div>
                    <div class="legend-item"><span class="legend-box" style="background:#0d9488;"></span> <span>15–30 min (Bonne accessibilité)</span></div>
                    <div class="legend-item"><span class="legend-box" style="background:#eab308;"></span> <span>30–45 min (Intermédiaire)</span></div>
                    <div class="legend-item"><span class="legend-box" style="background:#f97316;"></span> <span>45–60 min (Limitée)</span></div>
                    <div class="legend-item"><span class="legend-box" style="background:#dc2626;"></span> <span>> 60 min (Critique / Éloignée)</span></div>
                `;
            }}

            if (chkHydro) {{
                html += `
                    <div style="font-weight:700; color:#0f172a; margin:8px 0 6px;">Hydrographie :</div>
                    <div class="legend-item"><span class="legend-box" style="background:#0284c7; height:4px;"></span> <span>Oueds majeurs (Strahler 1-2)</span></div>
                    <div class="legend-item"><span class="legend-box" style="background:#38bdf8; height:2px;"></span> <span>Rivières secondaires</span></div>
                `;
            }}

            if (chkHazards) {{
                html += `
                    <div style="font-weight:700; color:#0f172a; margin:8px 0 6px;">Contraintes territoriales ABHL :</div>
                    <div class="legend-item"><span class="legend-box" style="background:#0284c7; opacity:0.6;"></span> <span>Plaines submersibles (Crues)</span></div>
                    <div class="legend-item"><span class="legend-box" style="background:#ea580c; opacity:0.6;"></span> <span>Versants instables (Glissements)</span></div>
                `;
            }}

            if (chkIso) {{
                html += `
                    <div style="font-weight:700; color:#0f172a; margin:8px 0 6px;">Zones d'accès estimées (Buffer) :</div>
                    <div class="legend-item"><span class="legend-box" style="background:#047857; opacity:0.4;"></span> <span>Seuil ≤ 15 min</span></div>
                    <div class="legend-item"><span class="legend-box" style="background:#0d9488; opacity:0.4;"></span> <span>Seuil ≤ 30 min</span></div>
                    <div class="legend-item"><span class="legend-box" style="background:#eab308; opacity:0.4;"></span> <span>Seuil ≤ 45 min</span></div>
                    <div class="legend-item"><span class="legend-box" style="background:#f97316; opacity:0.4;"></span> <span>Seuil ≤ 60 min</span></div>
                `;
            }}

            container.innerHTML = html;
        }}
        try {{
            updateLegend();
        }} catch(err) {{
            console.error("Erreur lors de updateLegend :", err);
        }}

    </script>
</body>
</html>
"""
    return html_content
