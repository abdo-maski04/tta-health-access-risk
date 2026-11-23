"""Theme visuel centralise de la plateforme TTA."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    navy: str = "#0B2235"
    navy_dark: str = "#12364A"
    blue: str = "#2878B5"
    turquoise: str = "#159B8E"
    green: str = "#27966F"
    orange: str = "#E5A13A"
    red: str = "#CE5252"
    grey: str = "#DCE3E9"
    background: str = "#F4F6F8"
    surface: str = "#FFFFFF"
    border: str = "#E5EAF0"
    text: str = "#172B3A"
    text_muted: str = "#718096"


THEME = Theme()

COLORS = {
    "overview_milieu": {
        "Urbain": "#0D5C75",
        "Mixte": "#2A9D8F",
        "Rural": "#E9C46A",
    },
    "overview_chart": {
        "primary": "#0D5C75",
        "secondary": "#178582",
        "rural": "#38A3A5",
        "amber": "#E09F3E",
        "alert": "#E63946",
        "positive": "#10B981",
    },
    "risk_milieu": {
        "Urbain": "#3B82F6",
        "Mixte": "#10B981",
        "Rural": "#F59E0B",
        "Non assigné": "#94A3B8",
    },
    "risk_facility": {
        "hospital": "#1D4ED8",
        "clinic": "#DC2626",
        "pharmacy": "#16A34A",
        "doctors": "#D97706",
        "laboratory": "#7C3AED",
        "other": "#475569",
    },
    "milieu": {
        "Urbain": "#279B91",
        "Mixte": "#E6AD55",
        "Rural": "#648BB8",
    },
    "province": [
        THEME.navy,
        THEME.turquoise,
        THEME.blue,
        "#6C63A8",
        THEME.green,
        THEME.orange,
        THEME.red,
        THEME.text_muted,
    ],
    "map_scale": ["#EAF4F5", "#79C5BD", THEME.blue, THEME.navy],
    "facility": {
        "hospital": THEME.navy_dark,
        "clinic": THEME.blue,
        "doctors": THEME.turquoise,
        "laboratory": THEME.orange,
        "pharmacy": THEME.green,
        "physiotherapist": THEME.red,
        "healthcare_unspecified": THEME.grey,
    },
}

APP_CSS = f"""
<style>
:root {{
    --tta-header-height: 3.75rem;
    --tta-navy: {THEME.navy};
    --tta-navy-secondary: {THEME.navy_dark};
    --tta-blue: {THEME.blue};
    --tta-turquoise: {THEME.turquoise};
    --tta-green: {THEME.green};
    --tta-orange: {THEME.orange};
    --tta-red: {THEME.red};
    --tta-grey: {THEME.grey};
    --tta-background: {THEME.background};
    --tta-surface: {THEME.surface};
    --tta-border: {THEME.border};
    --tta-text: {THEME.text};
    --tta-text-muted: {THEME.text_muted};
    --tta-card-shadow: 0 4px 16px rgba(11, 34, 53, 0.045);
}}

html, body {{
    font-family: Inter, "Segoe UI", sans-serif;
}}
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {{
    background: var(--tta-background);
    color: var(--tta-text);
}}
[data-testid="stMainBlockContainer"] {{
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
    padding: 1rem clamp(0.75rem, 2.5vw, 1.5rem);
}}
[data-testid="stHeader"] {{
    background: transparent;
}}

[data-testid="stSidebar"][aria-expanded="true"] {{
    width: 230px !important;
    min-width: 230px !important;
    max-width: 230px !important;
}}
[data-testid="stSidebar"] {{
    background: var(--tta-surface);
    border-right: 1px solid var(--tta-border);
}}
[data-testid="stSidebar"] [data-testid="stImage"] {{
    margin: 8px 0 4px;
    overflow: hidden;
}}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] {{
    display: none !important;
}}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
    color: var(--tta-navy);
}}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {{
    gap: 6px;
}}
[data-testid="stSidebar"] [role="radiogroup"] label {{
    min-height: 40px;
    margin: 0;
    padding: 9px 12px;
    border-radius: 8px;
    color: var(--tta-navy-secondary);
    font-size: 13px;
    font-weight: 500;
    transition: background-color 140ms ease, color 140ms ease;
    cursor: pointer;
}}
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child {{
    display: none !important;
}}
[data-testid="stSidebar"] [role="radiogroup"] input[type="radio"] {{
    display: none !important;
}}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {{
    background: rgba(21, 155, 142, 0.08);
    color: var(--tta-turquoise);
}}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
    background: #159B8E !important;
    color: #FFFFFF !important;
    font-weight: 600;
    box-shadow: 0 4px 12px rgba(8, 127, 140, 0.35);
}}
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="input"] > div,
[data-testid="stSidebar"] textarea {{
    background: #FFFFFF;
    border-color: var(--tta-border);
    border-radius: 8px;
    color: #fff;
}}
[data-testid="stSidebar"] input {{
    color: var(--tta-text);
}}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] .tta-sidebar-brand {{
    padding: 8px 4px 18px;
}}
.tta-sidebar-subtitle {{
    margin: 3px 4px 10px;
    color: var(--tta-text-muted);
    font-size: 10px;
    line-height: 1.45;
}}
.tta-sidebar-footer {{
    margin-top: 20px;
    padding: 11px 10px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    color: rgba(255, 255, 255, 0.68);
    font-size: 11px;
    line-height: 1.6;
}}
.tta-sidebar-territory-card {{
    margin-top: 35px;
    padding: 14px 12px;
    background: #F5F7FA;
    border: 1px solid var(--tta-border);
    border-radius: 10px;
}}
.tta-sidebar-card-label {{
    color: var(--tta-text-muted);
    font-size: 11px;
    font-weight: 500;
    margin-bottom: 4px;
}}
.tta-sidebar-card-select {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 10px;
    background: #FFFFFF;
    border: 1px solid var(--tta-border);
    border-radius: 6px;
    color: var(--tta-navy);
    font-size: 12px;
    font-weight: 600;
}}
.tta-sidebar-card-date {{
    color: var(--tta-navy-secondary);
    font-size: 11px;
    font-weight: 500;
    margin-bottom: 12px;
}}
.tta-sidebar-status-pill {{
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 5px 10px;
    background: rgba(16, 185, 129, 0.14);
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-radius: 20px;
    color: #34D399;
    font-size: 11px;
    font-weight: 600;
}}
.tta-status-dot {{
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background-color: #10B981;
    display: inline-block;
    box-shadow: 0 0 6px #10B981;
}}
.tta-sidebar-bottom-footer {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 18px;
    padding: 6px 4px;
    color: var(--tta-text-muted);
    font-size: 12px;
}}
.tta-settings-icon {{
    font-size: 14px;
}}
.tta-version-text {{
    font-size: 11px;
    font-family: monospace;
}}
.tta-sidebar-version {{
    padding: 10px 4px 2px;
    color: rgba(255, 255, 255, 0.58);
    font-size: 10px;
}}

.tta-header {{
    display: flex;
    align-items: center;
    gap: 14px;
    background: var(--tta-surface);
    border: 1px solid var(--tta-border);
    border-radius: 13px;
    padding: 17px 21px;
    margin-bottom: 16px;
    box-shadow: var(--tta-card-shadow);
}}
.tta-app-topbar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    min-height: auto;
    margin: 0 0 1rem;
    padding: 0.65rem 1.5rem;
    box-sizing: border-box;
    background: var(--tta-navy);
    color: #FFFFFF;
    box-shadow: 0 2px 10px rgba(11, 34, 53, 0.18);
}}
.tta-app-brand, .tta-app-region {{
    display: flex;
    align-items: center;
    gap: 10px;
}}
.tta-app-brand strong {{
    display: block;
    font-size: 15px;
    letter-spacing: 0.3px;
}}
.tta-app-brand small {{
    display: block;
    color: rgba(255,255,255,0.72);
    font-size: 10px;
    font-style: italic;
}}
.tta-app-brand-mark {{
    color: #16D4D0;
    font-size: 28px;
    font-weight: 800;
}}
.tta-app-region {{
    color: rgba(255,255,255,0.94);
    font-size: 13px;
    font-weight: 650;
}}
.tta-app-action, .tta-app-menu {{
    margin-left: 18px;
    color: rgba(255,255,255,0.88);
    font-size: 18px;
}}
.tta-app-menu {{
    border-left: 1px solid rgba(255,255,255,0.42);
    padding-left: 18px;
}}
.tta-header-icon {{
    display: inline-flex;
    flex: 0 0 44px;
    width: 44px;
    height: 44px;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: #087F8C;
    color: #FFFFFF;
    font-size: 20px;
}}
.tta-header-content h1 {{
    color: var(--tta-navy);
    font-size: 23px;
    font-weight: 750;
    line-height: 1.2;
    margin: 0 0 3px;
}}
.tta-header-content p {{
    color: var(--tta-text-muted);
    font-size: 13px;
    line-height: 1.4;
    margin: 0;
}}
.tta-header-update {{
    color: var(--tta-text-muted);
    font-size: 11px;
    margin-top: 6px;
}}

.tta-kpi {{
    min-height: 84px;
    padding: 10px 12px 9px;
    background: var(--tta-surface);
    border: 1px solid var(--tta-border);
    border-radius: 11px;
    box-shadow: var(--tta-card-shadow);
}}
.tta-kpi-heading {{
    display: flex;
    align-items: center;
    gap: 8px;
}}
.tta-kpi-icon {{
    display: inline-flex;
    width: 26px;
    height: 26px;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    background: rgba(8, 127, 140, 0.1);
    color: #087F8C;
    font-size: 15px;
}}
.tta-kpi-label {{
    color: var(--tta-text-muted);
    font-size: 11px;
    font-weight: 650;
    line-height: 1.25;
}}
.tta-kpi-value {{
    color: var(--tta-navy);
    font-size: 20px;
    font-weight: 750;
    line-height: 1.2;
    margin: 5px 0 2px;
    letter-spacing: -0.02em;
}}
.tta-kpi-badge-green {{
    display: inline-flex;
    align-items: center;
    gap: 3px;
    background: rgba(16, 185, 129, 0.12);
    color: #10B981;
    padding: 2px 7px;
    border-radius: 12px;
    font-weight: 600;
    font-size: 10px;
}}
    font-weight: 750;
    line-height: 1.2;
    margin: 5px 0 3px;
    letter-spacing: -0.02em;
}}
.tta-kpi-unit {{
    color: var(--tta-text-muted);
    font-size: 12px;
    font-weight: 550;
    margin-left: 5px;
    letter-spacing: 0;
}}
.tta-kpi-description {{
    color: var(--tta-text-muted);
    font-size: 9px;
    line-height: 1.4;
    min-height: 13px;
}}
.tta-kpi-source {{
    color: var(--tta-text-muted);
    font-size: 8px;
    margin-top: 4px;
}}

.tta-card {{
    background: var(--tta-surface);
    border: 1px solid var(--tta-border);
    border-radius: 11px;
    padding: 12px 14px;
    box-shadow: var(--tta-card-shadow);
}}
.tta-card-title {{
    color: var(--tta-navy-secondary);
    font-size: 13px;
    font-weight: 700;
    line-height: 1.35;
    margin-bottom: 8px;
}}
[data-testid="stPlotlyChart"] {{
    overflow: hidden;
    background: var(--tta-surface);
    border: 0;
    border-radius: 8px;
    padding: 0;
}}
[data-testid="stVerticalBlockBorderWrapper"] {{
    background: var(--tta-surface);
    border-color: var(--tta-border);
    border-radius: 10px;
    box-shadow: var(--tta-card-shadow);
}}
[data-testid="stVerticalBlockBorderWrapper"] > div {{
    padding: 9px 10px;
}}
[data-testid="stDataFrame"] {{
    overflow: hidden;
    border: 1px solid var(--tta-border);
    border-radius: 9px;
}}
[data-testid="stCustomComponentV1"] iframe {{
    border: 1px solid var(--tta-border);
    border-radius: 10px;
}}

.tta-source {{
    display: flex;
    align-items: flex-start;
    gap: 9px;
    color: var(--tta-text-muted);
    background: rgba(40, 120, 181, 0.045);
    border: 1px solid var(--tta-border);
    border-radius: 9px;
    font-size: 10px;
    line-height: 1.5;
    margin: 8px 0 14px;
    padding: 8px 11px;
}}
.tta-source-icon {{
    display: inline-flex;
    flex: 0 0 19px;
    width: 19px;
    height: 19px;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: rgba(40, 120, 181, 0.12);
    color: var(--tta-blue);
    font-size: 11px;
    font-weight: 750;
}}
.tta-source-content {{
    min-width: 0;
}}
.tta-empty {{
    background: var(--tta-surface);
    border: 1px dashed var(--tta-border);
    border-radius: 10px;
    color: var(--tta-text-muted);
    padding: 24px;
    text-align: center;
}}
.tta-empty-title {{
    color: var(--tta-text);
    font-weight: 700;
    margin-bottom: 6px;
}}
.tta-table-empty {{
    color: var(--tta-text-muted);
    padding: 16px 4px;
    font-size: 12px;
}}

.stButton > button {{
    border: 1px solid var(--tta-border);
    border-radius: 8px;
    color: var(--tta-navy-secondary);
    background: #FFFFFF;
    font-weight: 600;
}}
.stButton > button:hover {{
    border-color: var(--tta-turquoise);
    color: var(--tta-turquoise);
    background: rgba(21, 155, 142, 0.06);
}}
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] button {{
    border: 1px solid var(--tta-border) !important;
    border-radius: 8px !important;
    background: #FFFFFF !important;
    color: var(--tta-navy-secondary) !important;
}}
[data-testid="stSidebar"] .stButton > button:hover,
[data-testid="stSidebar"] button:hover {{
    border-color: var(--tta-turquoise) !important;
    color: var(--tta-turquoise) !important;
    background: rgba(21, 155, 142, 0.06) !important;
}}
body:has(.tta-overview) [data-testid="stSidebar"][aria-expanded="true"] {{
    width: 210px !important;
    min-width: 210px !important;
    max-width: 210px !important;
}}
body:has(.tta-overview) [data-testid="stSidebar"] {{
    background: #FFFFFF !important;
    border-right: 1px solid #E2E8F0 !important;
}}
body:has(.tta-overview) [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
body:has(.tta-overview) [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
body:has(.tta-overview) [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
body:has(.tta-overview) [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3,
body:has(.tta-overview) [data-testid="stSidebar"] label,
body:has(.tta-overview) [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
    color: #334155 !important;
}}
body:has(.tta-overview) [data-testid="stSidebar"] [role="radiogroup"] label {{
    color: #334155 !important;
    min-height: 36px;
    padding: 8px 10px 8px 12px;
    border: 0;
    border-radius: 10px;
    background: transparent;
}}
body:has(.tta-overview) [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
    background: #0D5C75 !important;
    color: #FFFFFF !important;
    box-shadow: none !important;
}}
body:has(.tta-overview) [data-testid="stSidebar"] [data-testid="stImage"] {{
    margin: 0 0 3px;
}}
body:has(.tta-overview) [data-testid="stSidebar"] [data-testid="stImage"] img {{
    max-height: 50px;
    object-fit: contain;
    object-position: left center;
}}
body:has(.tta-overview) [data-testid="stSidebar"] .tta-sidebar-territory-card {{
    background: #F8FAFC;
    border-color: #E2E8F0;
    margin-top: 20px;
}}
body:has(.tta-overview) [data-testid="stSidebar"] .tta-sidebar-card-label,
body:has(.tta-overview) [data-testid="stSidebar"] .tta-sidebar-card-date,
body:has(.tta-overview) [data-testid="stSidebar"] .tta-sidebar-bottom-footer {{
    color: #1E293B;
}}
body:has(.tta-overview) [data-testid="stSidebar"] .tta-sidebar-card-select {{
    background: #FFFFFF;
    color: #1E293B;
    border-color: #E2E8F0;
}}
body:has(.tta-overview) [data-testid="stMainBlockContainer"] {{
    max-width: none;
    padding: .5rem 1rem 1rem;
}}
body:has(.tta-overview) [data-testid="stAppViewContainer"],
body:has(.tta-overview) [data-testid="stMain"] {{
    background: #F4F7F9;
    color: #0F172A;
}}
body:has(.tta-overview) .tta-header-content h1,
body:has(.tta-overview) .tta-card-title {{
    color: #0F172A;
}}
body:has(.tta-overview) .tta-header-content p {{
    color: #64748B;
}}
body:has(.tta-overview) .tta-app-topbar {{
    display: none;
}}
body:has(.tta-overview) .tta-header {{
    background: transparent;
    border: 0;
    box-shadow: none;
    padding: 4px 2px 9px;
    margin: 0;
}}
body:has(.tta-overview) .tta-header-icon {{
    border-radius: 10px;
    background: #178582;
}}
body:has(.tta-overview) .tta-overview-toolbar {{
    margin-bottom: 5px;
}}
body:has(.tta-overview) .tta-overview-toolbar [data-testid="stVerticalBlockBorderWrapper"] > div {{
    padding: 7px 10px;
}}
body:has(.tta-overview) [data-testid="stMain"] .tta-kpi {{
    min-height: 79px;
    padding: 9px 9px 7px;
    border-radius: 10px;
}}
body:has(.tta-overview) [data-testid="stMain"] .tta-kpi-label {{
    font-size: 10px;
}}
body:has(.tta-overview) [data-testid="stMain"] .tta-kpi-value {{
    font-size: 18px;
}}
body:has(.tta-overview) [data-testid="stMain"] .tta-kpi-icon {{
    background: rgba(23,133,130,.1);
    color: #178582;
}}
body:has(.tta-overview) [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {{
    border-radius: 10px;
    border-color: #E2E8F0;
    background: #FFFFFF;
    box-shadow: 0 1px 3px rgba(0,0,0,.04);
}}
body:has(.tta-overview) [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] > div {{
    padding: 8px 10px;
}}
body:has(.tta-overview) [data-testid="stMain"] [data-testid="stPlotlyChart"] {{
    min-height: 0;
}}
body:has(.tta-overview) [data-testid="stMain"] [data-testid="stDataFrame"] {{
    border-radius: 7px;
}}
body:has(.tta-overview) .tta-overview-toolbar [data-testid="stButton"] button {{
    min-height: 36px;
}}
body:has(.tta-overview) [data-testid="stSidebar"] .tta-sidebar-project {{
    color: #FFFFFF;
    font-size: 15px;
    font-weight: 700;
    line-height: 1.25;
}}
body:has(.tta-overview) [data-testid="stSidebar"] .tta-sidebar-subtitle {{
    color: rgba(255,255,255,.72);
    margin: 3px 0 10px;
}}
.tta-overview-notification {{
    color: #0D5C75;
    font-size: 20px;
    line-height: 36px;
    text-align: center;
}}
.tta-overview-user {{
    color: #334155;
    font-size: 11px;
    font-weight: 650;
    line-height: 36px;
    white-space: nowrap;
}}
body:has(.tta-overview) .tta-source {{
    background: #EFF6FF;
    border-left: 4px solid #0D5C75;
    border-radius: 8px;
}}
@media (max-width: 68.75rem) {{
    body:has(.tta-overview) [data-testid="stSidebar"][aria-expanded="true"] {{
        width: 190px !important;
        min-width: 190px !important;
        max-width: 190px !important;
    }}
}}
@media (max-width: 47.5rem) {{
    [data-testid="stMainBlockContainer"] {{
        padding: 0.75rem clamp(0.75rem, 3vw, 1.25rem);
    }}
    .tta-header {{
        padding: 14px;
    }}
    .tta-header-content h1 {{
        font-size: 21px;
    }}
}}

[data-testid="stSidebar"] {{
    background: #0A3642 !important;
    border-right: 1px solid rgba(255,255,255,.1) !important;
}}
[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"]:has(.tta-sidebar-territory-card) {{
    min-height: calc(100vh - 72px);
}}
[data-testid="stSidebarUserContent"] [data-testid="stElementContainer"]:has(.tta-sidebar-territory-card) {{
    margin-top: auto;
}}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
    color: #FFFFFF !important;
}}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {{
    gap: 5px;
}}
[data-testid="stSidebar"] [role="radiogroup"] label {{
    min-height: 38px;
    margin: 0;
    padding: 8px 10px 8px 12px;
    border-left: 3px solid transparent;
    border-radius: 6px;
    color: rgba(255,255,255,.84) !important;
    font-size: 13px;
}}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
    background: #165363 !important;
    border-left-color: #14B8A6 !important;
    color: #FFFFFF !important;
    box-shadow: none !important;
}}
.tta-sidebar-territory-card {{
    background: #072832 !important;
    border-color: rgba(255,255,255,.1) !important;
    margin-top: 20px;
}}
.tta-sidebar-card-label,
.tta-sidebar-card-date,
.tta-sidebar-bottom-footer {{
    color: rgba(255,255,255,.75) !important;
}}
.tta-sidebar-card-select {{
    background: rgba(255,255,255,.08) !important;
    border-color: rgba(255,255,255,.14) !important;
    color: #FFFFFF !important;
}}
.tta-app-topbar {{
    min-height: 58px;
    margin: 0 0 14px;
    padding: 0 18px;
    background: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
    color: #0F172A;
    box-shadow: none;
}}
.tta-global-header {{
    width: 100%;
    min-height: auto;
    margin: 0 0 1rem;
    padding: 0.65rem 1.5rem;
    box-sizing: border-box;
    background: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
}}
.tta-global-header [data-testid="stImage"] {{
    margin: 0;
}}
.tta-global-header-region {{
    color: #334155;
    font-size: clamp(0.75rem, 1vw, 0.875rem);
    font-weight: 650;
    line-height: 1.25;
    overflow-wrap: anywhere;
}}
.tta-global-header-page {{
    color: #64748B;
    font-size: clamp(0.75rem, 1vw, 0.875rem);
    line-height: 1.25;
    text-align: right;
    overflow-wrap: anywhere;
}}
body:has(.tta-map-screen) [data-testid="stMainBlockContainer"] {{
    max-width: none !important;
    padding: 0 !important;
}}
body:has(.tta-map-screen) [data-testid="stSidebar"][aria-expanded="true"] {{
    width: 230px !important;
    min-width: 230px !important;
    max-width: 230px !important;
}}
body:has(.tta-map-screen) [data-testid="stSidebar"][aria-expanded="false"] {{
    width: 0 !important;
    min-width: 0 !important;
}}
[data-testid="stSidebar"][data-collapsed="false"] {{
    width: 250px !important;
    min-width: 250px !important;
    max-width: 250px !important;
}}
[data-testid="stSidebar"][data-collapsed="true"],
[data-testid="stSidebar"][aria-expanded="false"] {{
    width: 0 !important;
    min-width: 0 !important;
    max-width: 0 !important;
}}
[data-testid="stSidebar"][data-collapsed="false"],
[data-testid="stSidebar"][aria-expanded="true"] {{
    width: 250px !important;
    min-width: 250px !important;
    max-width: 250px !important;
}}
[data-testid="stToolbar"] {{
    display: flex !important;
    visibility: visible !important;
    background: transparent !important;
    height: auto !important;
    pointer-events: none !important;
    z-index: 999999 !important;
}}
[data-testid="stToolbarActions"],
[data-testid="stStatusWidget"],
[data-testid="stDecoration"],
#MainMenu {{
    display: none !important;
}}
[data-testid="stExpandSidebarButton"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
button[aria-label="Expand sidebar"],
button[aria-label="Collapse sidebar"],
button[aria-label="Open sidebar"],
button[aria-label="Close sidebar"] {{
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
    z-index: 1000000 !important;
}}
[data-testid="stExpandSidebarButton"] button,
[data-testid="stSidebarCollapseButton"] button,
[data-testid="collapsedControl"] button,
[data-testid="stSidebarCollapsedControl"] button,
button[aria-label="Expand sidebar"],
button[aria-label="Collapse sidebar"],
button[aria-label="Open sidebar"],
button[aria-label="Close sidebar"] {{
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    border-radius: 8px !important;
    background: #0D5C75 !important;
    color: #FFFFFF !important;
    border: 1px solid #0A3642 !important;
    padding: 6px !important;
    min-width: 36px !important;
    min-height: 36px !important;
    cursor: pointer !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18) !important;
}}
[data-testid="stExpandSidebarButton"] button:hover,
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="collapsedControl"] button:hover,
[data-testid="stSidebarCollapsedControl"] button:hover,
button[aria-label="Expand sidebar"]:hover,
button[aria-label="Collapse sidebar"]:hover,
button[aria-label="Open sidebar"]:hover,
button[aria-label="Close sidebar"]:hover {{
    background: #0A3642 !important;
    border-color: #07252D !important;
}}
[data-testid="stExpandSidebarButton"] svg,
[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"],
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"],
[data-testid="collapsedControl"] svg,
[data-testid="stSidebarCollapsedControl"] svg {{
    color: #FFFFFF !important;
    fill: #FFFFFF !important;
}}
body:has([data-testid="stSidebar"][data-collapsed="true"]) [data-testid="stExpandSidebarButton"],
body:has([data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stExpandSidebarButton"],
body:has([data-testid="stSidebar"][data-collapsed="true"]) [data-testid="collapsedControl"],
body:has([data-testid="stSidebar"][aria-expanded="false"]) [data-testid="collapsedControl"],
body:has([data-testid="stSidebar"][data-collapsed="true"]) [data-testid="stSidebarCollapsedControl"],
body:has([data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stSidebarCollapsedControl"],
body:has([data-testid="stSidebar"][data-collapsed="true"]) button[aria-label="Expand sidebar"],
body:has([data-testid="stSidebar"][aria-expanded="false"]) button[aria-label="Expand sidebar"],
body:has([data-testid="stSidebar"][data-collapsed="true"]) button[aria-label="Open sidebar"],
body:has([data-testid="stSidebar"][aria-expanded="false"]) button[aria-label="Open sidebar"] {{
    position: fixed !important;
    top: 10px !important;
    left: 10px !important;
    z-index: 1000000 !important;
}}
body:has([data-testid="stSidebar"][data-collapsed="true"])
    .st-key-tta-global-header [data-testid="stHorizontalBlock"],
body:has([data-testid="stSidebar"][aria-expanded="false"])
    .st-key-tta-global-header [data-testid="stHorizontalBlock"] {{
    padding-left: 3.5rem !important;
}}
header[data-testid="stHeader"] {{
    height: auto !important;
    min-height: 0 !important;
    background: transparent !important;
    overflow: visible !important;
    pointer-events: none !important;
    z-index: 999990 !important;
}}
.block-container,
[data-testid="stMainBlockContainer"] {{
    padding-top: 0 !important;
    margin-top: 0 !important;
}}
[data-testid="stMainBlockContainer"] [data-testid="stElementContainer"]:has(style),
[data-testid="stMainBlockContainer"] [data-testid="stElementContainer"]:has(.tta-overview),
body:has(.tta-map-screen) [data-testid="stMainBlockContainer"]
    [data-testid="stElementContainer"]:has(.tta-map-screen) {{
    display: none !important;
}}
.st-key-tta-global-header {{
    box-sizing: border-box;
    display: flex;
    width: 100%;
    min-height: var(--tta-header-height);
    height: auto;
    margin: 0 0 1rem 0 !important;
    margin-left: 0 !important;
    padding: 0.65rem 1.5rem 0.65rem 0 !important;
    padding-left: 0 !important;
    background: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
}}
.st-key-tta-global-header [data-testid="stHorizontalBlock"] {{
    display: flex;
    width: 100%;
    min-height: var(--tta-header-height);
    height: auto;
    justify-content: space-between;
    align-items: center;
    gap: clamp(0.5rem, 1.5vw, 1.5rem);
}}
.st-key-tta-global-header [data-testid="column"] {{
    flex: 1 1 0;
    min-width: 0;
}}
.st-key-tta-global-header [data-testid="stImage"] {{
    display: flex;
    width: 100%;
    height: auto;
    align-items: center;
    margin: 0 !important;
}}
.st-key-tta-global-header [data-testid="stImage"] img {{
    width: clamp(8rem, 15vw, 11.5rem) !important;
    max-width: 100%;
    height: auto !important;
    max-height: 2.625rem;
    object-fit: contain;
    object-position: left center;
}}
.st-key-tta-global-header [data-testid="stPopover"] {{
    display: flex !important;
    align-items: center !important;
}}
.st-key-tta-global-header [data-testid="stPopover"] > button {{
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: #0D5C75 !important;
    color: #FFFFFF !important;
    border: 1px solid #0A3642 !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    border-radius: 8px !important;
    padding: 6px 14px !important;
    min-height: 36px !important;
    height: 36px !important;
    box-shadow: 0 2px 6px rgba(13, 92, 117, 0.25) !important;
    cursor: pointer !important;
}}
.st-key-tta-global-header [data-testid="stPopover"] > button:hover {{
    background: #0A3642 !important;
    border-color: #07252D !important;
}}
.st-key-tta-global-header [data-testid="stPopover"] > button p {{
    color: #FFFFFF !important;
    font-weight: 700 !important;
    margin: 0 !important;
}}
body:has([data-testid="stSidebar"][data-collapsed="true"])
    .st-key-tta-global-header [data-testid="stHorizontalBlock"] {{
    padding-left: 3rem;
}}
.st-key-tta-overview-toolbar {{
    box-sizing: border-box;
    margin: 0 0 14px;
    padding: 4px 10px;
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 9px;
}}
.st-key-tta-overview-toolbar [data-testid="stHorizontalBlock"] {{
    min-height: 46px;
    align-items: center;
}}
.st-key-tta-overview-toolbar [data-testid="stImage"] {{
    margin: 0 !important;
}}
.tta-global-header-region {{
    text-align: center;
}}
.tta-global-header-page {{
    text-align: right;
}}
.st-key-tta-overview-toolbar [data-testid="stPopover"] > button {{
    min-height: 36px;
    border-color: #E2E8F0;
    background: #FFFFFF;
    color: #0D5C75;
    font-weight: 650;
    white-space: nowrap;
}}
body:has(.tta-overview) .tta-evolution-value {{
    color: #0D5C75;
    font-size: 17px;
    font-weight: 700;
    line-height: 1.15;
    white-space: nowrap;
}}
body:has(.tta-overview) .tta-evolution-label {{
    color: #64748B;
    font-size: 10px;
    margin-bottom: 3px;
}}
body [data-testid="stMainBlockContainer"] {{
    box-sizing: border-box;
    width: 100% !important;
    max-width: 100% !important;
    padding: 1rem clamp(0.75rem, 2.5vw, 1.5rem) !important;
}}
@media (max-width: 47.5rem) {{
    .st-key-tta-global-header {{
        padding: 0.6rem 1rem;
    }}
    .st-key-tta-global-header [data-testid="stHorizontalBlock"] {{
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
        grid-template-rows: auto auto;
        gap: 0.25rem 0.75rem;
    }}
    .st-key-tta-global-header [data-testid="column"] {{
        width: auto !important;
        min-width: 0;
    }}
    .st-key-tta-global-header [data-testid="column"]:first-child {{
        grid-column: 1;
        grid-row: 1;
    }}
    .st-key-tta-global-header [data-testid="column"]:nth-child(2) {{
        grid-column: 1 / -1;
        grid-row: 2;
        text-align: center;
    }}
    .st-key-tta-global-header [data-testid="column"]:last-child {{
        grid-column: 2;
        grid-row: 1;
    }}
    .st-key-tta-global-header .tta-global-header-region {{
        text-align: center;
    }}
}}
button[kind="primary"], [data-testid="stBaseButton-primary"] {{
    background-color: #0D5C75 !important;
    border-color: #0D5C75 !important;
    color: #FFFFFF !important;
}}
button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover {{
    background-color: #0A3642 !important;
    border-color: #0A3642 !important;
    color: #FFFFFF !important;
}}
div[data-stale="true"],
.stApp [data-stale="true"] {{
    opacity: 1 !important;
    filter: none !important;
    transition: none !important;
}}
div[data-testid="stStatusWidget"] {{
    visibility: hidden !important;
}}
[data-testid="stAppViewContainer"] .main,
[data-testid="stAppViewContainer"] .main .block-container {{
    background-color: #F4F7F9 !important;
}}
[data-stale="true"] {{
    display: none !important;
}}
body [data-testid="stSidebar"] {{
    background: #FFFFFF !important;
    border-right: 1px solid #E2E8F0 !important;
}}
body [data-testid="stSidebarContent"] {{
    padding-top: 0 !important;
}}
body [data-testid="stSidebar"] [data-testid="stImage"] {{
    display: flex;
    justify-content: flex-start;
    margin: 0 !important;
}}
body [data-testid="stSidebar"] [data-testid="stImage"] img {{
    max-height: 48px;
    object-fit: contain;
    object-position: left center;
}}
body [data-testid="stSidebar"] .st-key-tta-sidebar-brand {{
    padding: 0 4px !important;
    margin: 0 !important;
}}
body [data-testid="stSidebar"] .tta-sidebar-divider {{
    height: 1px;
    margin: 0 4px 14px;
    background: #E2E8F0;
}}
body [data-testid="stSidebar"] [role="radiogroup"] {{
    gap: 6px !important;
}}
body [data-testid="stSidebar"] [role="radiogroup"] label {{
    display: flex;
    align-items: center;
    min-height: 42px;
    padding: 10px 14px !important;
    border: 0 !important;
    border-radius: 10px !important;
    background: transparent !important;
    color: #334155 !important;
    font-weight: 500 !important;
}}
body [data-testid="stSidebar"] [role="radiogroup"] label:not(:has(input:checked)) {{
    background-color: transparent !important;
    color: #334155 !important;
}}
body [data-testid="stSidebar"] [role="radiogroup"] label:not(:has(input:checked))
    :is(span, p, div) {{
    color: #334155 !important;
}}
body [data-testid="stSidebar"] [role="radiogroup"] label:not(:has(input:checked)) svg {{
    color: #64748B !important;
    stroke: #64748B !important;
}}
body [data-testid="stSidebar"] [role="radiogroup"] label:not(:has(input:checked)) img {{
    filter: none !important;
}}
body [data-testid="stSidebar"] [role="radiogroup"] label > div:nth-child(2) {{
    display: flex;
    align-items: center;
    gap: 10px;
}}
body [data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child {{
    display: none !important;
}}
body [data-testid="stSidebar"] [role="radiogroup"] label img {{
    display: inline-block;
    flex: 0 0 18px;
    width: 18px;
    height: 18px;
    margin: 0;
    filter: none;
}}
body [data-testid="stSidebar"] [role="radiogroup"] label:hover {{
    background: #F1F5F9 !important;
    color: #0D5C75 !important;
}}
body [data-testid="stSidebar"] [role="radiogroup"] label:not(:has(input:checked)):hover
    :is(span, p, div) {{
    color: #0D5C75 !important;
}}
body [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
    background: #0D5C75 !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    box-shadow: none !important;
}}
body [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked)
    :is(span, p, div, svg) {{
    color: #FFFFFF !important;
    stroke: #FFFFFF !important;
}}
body [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) img {{
    filter: brightness(0) invert(1) !important;
}}
body [data-testid="stSidebar"] .tta-sidebar-territory-card {{
    margin: auto 4px 0 !important;
    padding: 12px !important;
    background: #F8FAFC !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 10px;
}}
body [data-testid="stSidebar"] .tta-sidebar-card-label,
body [data-testid="stSidebar"] .tta-sidebar-card-date,
body [data-testid="stSidebar"] .tta-sidebar-bottom-footer {{
    color: #1E293B !important;
}}
body [data-testid="stSidebar"] .tta-sidebar-card-select {{
    background: #FFFFFF !important;
    border-color: #E2E8F0 !important;
    color: #1E293B !important;
}}
body [data-testid="stSidebar"] .tta-sidebar-status-pill {{
    background: #DCFCE7 !important;
    border-color: #BBF7D0 !important;
    color: #166534 !important;
}}
body [data-testid="stSidebar"] .tta-status-dot {{
    background: #16A34A !important;
    box-shadow: none !important;
}}
body [data-testid="stSidebar"] .tta-settings-icon svg {{
    width: 16px;
    height: 16px;
    stroke: #64748B;
}}
</style>
"""
