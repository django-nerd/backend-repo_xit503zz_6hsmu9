import os
from io import BytesIO
from typing import List, Optional, Literal

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

app = FastAPI(title="FLAME-Style UI Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Section(BaseModel):
    kind: Literal["hero", "features", "showcase", "stats", "cta"]
    title: Optional[str] = None
    subtitle: Optional[str] = None
    content: Optional[str] = None
    bullets: Optional[List[str]] = None
    accent: Optional[str] = None


class GeneratedDesign(BaseModel):
    prompt: str
    theme: Literal["dark", "light"] = "dark"
    primary: str
    secondary: str
    background_from: str
    background_to: str
    neon_glow: str
    sections: List[Section]
    spline_url: Optional[str] = None


class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Natural language description of the desired UI")
    style_profile: Optional[str] = Field(
        None,
        description="Optional style profile token returned from /api/style/analyze to influence palette",
    )


class StyleProfile(BaseModel):
    name: str = "custom"
    primary: Optional[str] = None
    secondary: Optional[str] = None
    background_from: Optional[str] = None
    background_to: Optional[str] = None
    neon_glow: Optional[str] = None
    radius_scale: Optional[str] = None  # xs/sm/md/lg/xl
    shadow_style: Optional[str] = None  # soft/hard/neon


class StyleAnalyzeResponse(BaseModel):
    profile: StyleProfile
    notes: str


def infer_palette(prompt: str):
    p = prompt.lower()
    if "green" in p or "web3" in p or "gaming" in p:
        return {
            "primary": "#22c55e",  # emerald-500
            "secondary": "#14b8a6",  # teal-500
            "background_from": "#0b1220",
            "background_to": "#0b1020",
            "neon_glow": "rgba(34,197,94,0.65)",
        }
    if "purple" in p or "ai" in p or "neon" in p:
        return {
            "primary": "#8b5cf6",
            "secondary": "#06b6d4",
            "background_from": "#0b0f1a",
            "background_to": "#0b0d16",
            "neon_glow": "rgba(139,92,246,0.65)",
        }
    if "blue" in p:
        return {
            "primary": "#60a5fa",
            "secondary": "#22d3ee",
            "background_from": "#0b1220",
            "background_to": "#0b0f1d",
            "neon_glow": "rgba(96,165,250,0.65)",
        }
    # default
    return {
        "primary": "#22d3ee",
        "secondary": "#8b5cf6",
        "background_from": "#0b0f1a",
        "background_to": "#0b0d16",
        "neon_glow": "rgba(34,211,238,0.65)",
    }


def generate_sections(prompt: str, palette: dict) -> List[Section]:
    p = prompt.lower()
    base_accent = palette["primary"]
    sections: List[Section] = []

    sections.append(
        Section(
            kind="hero",
            title="Futuristic Experience",
            subtitle="Describe what you want — get a production‑ready UI instantly.",
            content="High‑fidelity design with glassmorphism, neon accents, and smooth motion.",
            bullets=None,
            accent=base_accent,
        )
    )

    if "dashboard" in p:
        sections.append(
            Section(
                kind="stats",
                title="Realtime Metrics",
                subtitle="Key stats presented with clarity and glow.",
                bullets=["Active Users", "Conversion", "Revenue", "Latency"],
                accent=base_accent,
            )
        )

    sections.append(
        Section(
            kind="features",
            title="What You Get",
            subtitle="Crafted components and beautiful defaults.",
            bullets=[
                "Neon-highlighted CTAs",
                "Glass cards with depth",
                "Responsive grid layout",
                "Dark, cinematic theme",
            ],
            accent=base_accent,
        )
    )

    sections.append(
        Section(
            kind="showcase",
            title="Visual Showcase",
            subtitle="Abstract shapes and depth to match the FLAME aesthetic.",
            accent=base_accent,
        )
    )

    sections.append(
        Section(
            kind="cta",
            title="Export Instantly",
            subtitle="Download the full project as a zip and start building.",
            accent=base_accent,
        )
    )

    return sections


def build_design(prompt: str, profile: Optional[StyleProfile] = None) -> GeneratedDesign:
    palette = infer_palette(prompt)
    # Override with style profile if provided
    if profile is not None:
        palette.update({k: v for k, v in profile.model_dump().items() if k in palette and v})
    sections = generate_sections(prompt, palette)
    return GeneratedDesign(
        prompt=prompt,
        theme="dark",
        primary=palette["primary"],
        secondary=palette["secondary"],
        background_from=palette["background_from"],
        background_to=palette["background_to"],
        neon_glow=palette["neon_glow"],
        sections=sections,
        spline_url="https://prod.spline.design/4Zh-Q6DWWp5yPnQf/scene.splinecode",
    )


@app.get("/")
def root():
    return {"message": "FLAME-Style UI Generator API is running"}


@app.post("/api/generate", response_model=GeneratedDesign)
def generate(req: GenerateRequest):
    profile = None
    if req.style_profile:
        # Very simple token-based override: expect comma-separated key:value
        # e.g., "primary:#22c55e,neon_glow:rgba(34,197,94,0.65)"
        try:
            kv = {}
            for pair in req.style_profile.split(","):
                if ":" in pair:
                    k, v = pair.split(":", 1)
                    kv[k.strip()] = v.strip()
            profile = StyleProfile(**kv)
        except Exception:
            profile = None
    return build_design(req.prompt, profile)


class DownloadRequest(BaseModel):
    design: GeneratedDesign


def make_index_html(design: GeneratedDesign) -> str:
    # Use Tailwind via CDN for the downloadable package
    hero_iframe = f'<iframe src="{design.spline_url}" class="w-full h-[420px] rounded-3xl border border-white/10" style="background:transparent" allow="autoplay; fullscreen" loading="lazy"></iframe>'
    features_list = "".join(
        f'<li class="flex items-center gap-3"><span class="w-1.5 h-1.5 rounded-full" style="background:{design.primary}"></span><span class="text-slate-300">{b}</span></li>'
        for b in next((s.bullets for s in design.sections if s.kind == "features" and s.bullets), [])
    )

    return f"""
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Generated UI</title>
  <script src=\"https://cdn.tailwindcss.com\"></script>
  <style>
    :root {{ --primary: {design.primary}; --glow: {design.neon_glow}; }}
    .glow {{ box-shadow: 0 0 40px var(--glow), 0 0 120px var(--glow) inset; }}
    .glass {{ background: rgba(15,23,42,.55); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,.07); }}
    body {{ background: radial-gradient(1200px 800px at 10% 10%, rgba(99,102,241,.12), transparent 40%), linear-gradient(180deg, {design.background_from}, {design.background_to}); }}
  </style>
</head>
<body class=\"text-white min-h-screen\">
  <header class=\"max-w-7xl mx-auto px-6 py-10\">
    <div class=\"flex items-center justify-between\">
      <div class=\"text-xl font-semibold tracking-tight\">FLAME Generated</div>
      <a href=\"#\" class=\"px-4 py-2 rounded-lg\" style=\"background:var(--primary)\">Get Started</a>
    </div>
  </header>
  <main class=\"max-w-7xl mx-auto px-6 space-y-20\">
    <section class=\"grid lg:grid-cols-2 gap-10 items-center\">
      <div>
        <h1 class=\"text-5xl font-bold leading-tight mb-4\">{next((s.title for s in design.sections if s.kind=='hero'), 'Your Vision, Rendered') }</h1>
        <p class=\"text-slate-300 mb-6\">{next((s.subtitle for s in design.sections if s.kind=='hero'), '')}</p>
        <div class=\"flex items-center gap-4\">\n          <a class=\"px-5 py-3 rounded-xl glow\" style=\"background:var(--primary)\">Generate</a>\n          <a class=\"px-5 py-3 rounded-xl glass\">Learn more</a>\n        </div>
      </div>
      <div class=\"glass p-2 rounded-3xl\">{hero_iframe}</div>
    </section>

    <section class=\"grid lg:grid-cols-3 gap-6\">
      <div class=\"col-span-1 glass p-8 rounded-2xl\">
        <h3 class=\"text-xl mb-4\">{next((s.title for s in design.sections if s.kind=='features'), 'Features')}</h3>
        <ul class=\"space-y-3\">{features_list}</ul>
      </div>
      <div class=\"col-span-2 grid sm:grid-cols-2 gap-6\">\n        <div class=\"h-48 rounded-2xl glass\"></div>\n        <div class=\"h-48 rounded-2xl glow\"></div>\n        <div class=\"h-48 rounded-2xl glow\"></div>\n        <div class=\"h-48 rounded-2xl glass\"></div>\n      </div>
    </section>

    <section class=\"glass rounded-2xl p-10 flex items-center justify-between\">\n      <div>\n        <h3 class=\"text-2xl font-semibold mb-2\">{next((s.title for s in design.sections if s.kind=='cta'), 'Export Instantly')}</h3>\n        <p class=\"text-slate-300\">{next((s.subtitle for s in design.sections if s.kind=='cta'), '')}</p>\n      </div>\n      <a class=\"px-5 py-3 rounded-xl glow\" style=\"background:var(--primary)\">Download</a>\n    </section>
  </main>
</body>
</html>
"""


def build_zip_static(design: GeneratedDesign) -> BytesIO:
    from zipfile import ZipFile, ZIP_DEFLATED

    mem = BytesIO()
    with ZipFile(mem, mode="w", compression=ZIP_DEFLATED) as z:
        z.writestr("index.html", make_index_html(design))
        z.writestr(
            "README.md",
            "Generated UI package. Open index.html in a modern browser. Tailwind loaded via CDN.",
        )
    mem.seek(0)
    return mem


def build_zip_react(design: GeneratedDesign) -> BytesIO:
    """Create a minimal React project that renders the generated layout and styles.
    Uses Tailwind via CDN in index.html for simplicity (no install step required).
    """
    from zipfile import ZipFile, ZIP_DEFLATED

    index_html = f"""
<!doctype html>
<html>
  <head>
    <meta charset=\"UTF-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
    <title>FLAME React Export</title>
    <script src=\"https://cdn.tailwindcss.com\"></script>
    <style>
      :root {{ --primary: {design.primary}; --glow: {design.neon_glow}; }}
      .glow {{ box-shadow: 0 0 40px var(--glow), 0 0 120px var(--glow) inset; }}
      .glass {{ background: rgba(15,23,42,.55); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,.07); }}
      body {{ background: radial-gradient(1200px 800px at 10% 10%, rgba(99,102,241,.12), transparent 40%), linear-gradient(180deg, {design.background_from}, {design.background_to}); }}
    </style>
  </head>
  <body>
    <div id=\"root\"></div>
    <script type=\"module\" src=\"/main.js\"></script>
  </body>
</html>
"""

    main_js = """
import React from 'https://esm.sh/react@18.2.0'
import ReactDOM from 'https://esm.sh/react-dom@18.2.0/client'
import App from './App.js'

ReactDOM.createRoot(document.getElementById('root')).render(
  React.createElement(React.StrictMode, null, React.createElement(App))
)
"""

    title = next((s.title for s in design.sections if s.kind == 'hero'), 'Your Vision, Rendered')
    subtitle = next((s.subtitle for s in design.sections if s.kind == 'hero'), '')
    features_title = next((s.title for s in design.sections if s.kind == 'features'), 'Features')
    bullets = next((s.bullets for s in design.sections if s.kind == 'features' and s.bullets), [])

    bullets_js = "\n              ".join([
        "React.createElement('li', { className: 'flex items-center gap-3' }, React.createElement('span', { className: 'w-1.5 h-1.5 rounded-full', style: { background: '__PRIMARY__' } }), React.createElement('span', { className: 'text-slate-300' }, '" + str(b).replace("'", "\\'") + "'))"
        for b in bullets
    ])

    app_js_template = """
export default function App() {
  return (
    React.createElement('div', { className: 'text-white min-h-screen' },
      React.createElement('header', { className: 'max-w-7xl mx-auto px-6 py-10' },
        React.createElement('div', { className: 'flex items-center justify-between' },
          React.createElement('div', { className: 'text-xl font-semibold tracking-tight' }, 'FLAME Generated'),
          React.createElement('a', { href: '#', className: 'px-4 py-2 rounded-lg', style: { background: '__PRIMARY__' } }, 'Get Started')
        )
      ),
      React.createElement('main', { className: 'max-w-7xl mx-auto px-6 space-y-20' },
        React.createElement('section', { className: 'grid lg:grid-cols-2 gap-10 items-center' },
          React.createElement('div', null,
            React.createElement('h1', { className: 'text-5xl font-bold leading-tight mb-4' }, '__TITLE__'),
            React.createElement('p', { className: 'text-slate-300 mb-6' }, '__SUBTITLE__'),
            React.createElement('div', { className: 'flex items-center gap-4' },
              React.createElement('a', { className: 'px-5 py-3 rounded-xl glow', style: { background: '__PRIMARY__' } }, 'Generate'),
              React.createElement('a', { className: 'px-5 py-3 rounded-xl glass' }, 'Learn more')
            )
          ),
          React.createElement('div', { className: 'rounded-3xl overflow-hidden border border-white/10 h-[420px] glass' })
        ),
        React.createElement('section', { className: 'grid lg:grid-cols-3 gap-6' },
          React.createElement('div', { className: 'col-span-1 glass p-8 rounded-2xl' },
            React.createElement('h3', { className: 'text-xl mb-4' }, '__FEATURES_TITLE__'),
            React.createElement('ul', { className: 'space-y-3' },
              __BULLETS__
            )
          ),
          React.createElement('div', { className: 'col-span-2 grid sm:grid-cols-2 gap-6' },
            React.createElement('div', { className: 'h-48 rounded-2xl glass' }),
            React.createElement('div', { className: 'h-48 rounded-2xl glow' }),
            React.createElement('div', { className: 'h-48 rounded-2xl glow' }),
            React.createElement('div', { className: 'h-48 rounded-2xl glass' })
          )
        ),
        React.createElement('section', { className: 'glass rounded-2xl p-10 flex items-center justify-between' },
          React.createElement('div', null,
            React.createElement('h3', { className: 'text-2xl font-semibold mb-2' }, 'Export Instantly'),
            React.createElement('p', { className: 'text-slate-300' }, '')
          ),
          React.createElement('a', { className: 'px-5 py-3 rounded-xl glow', style: { background: '__PRIMARY__' } }, 'Download')
        )
      )
    )
  )
}
"""

    app_js = (
        app_js_template
        .replace('__TITLE__', str(title).replace("'", "\\'"))
        .replace('__SUBTITLE__', str(subtitle).replace("'", "\\'"))
        .replace('__FEATURES_TITLE__', str(features_title).replace("'", "\\'"))
        .replace('__BULLETS__', bullets_js)
        .replace('__PRIMARY__', design.primary)
    )

    mem = BytesIO()
    with ZipFile(mem, mode="w", compression=ZIP_DEFLATED) as z:
        z.writestr("index.html", index_html)
        z.writestr("main.js", main_js)
        z.writestr("App.js", app_js)
        z.writestr(
            "README.md",
            "React export using ESM imports and Tailwind CDN. Open index.html with a local server (due to module imports).",
        )
    mem.seek(0)
    return mem


@app.post("/api/download")
def download(req: DownloadRequest):
    try:
        buf = build_zip_static(req.design)
        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=generated-ui.zip"
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export/react")
def export_react(req: DownloadRequest):
    try:
        buf = build_zip_react(req.design)
        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=generated-react-ui.zip"
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/style/analyze", response_model=StyleAnalyzeResponse)
async def style_analyze(
    file: UploadFile = File(None, description="Optional uploaded HTML/CSS for analysis"),
    text: Optional[str] = Form(None, description="Optional raw HTML/CSS pasted as text"),
):
    """
    Analyze provided HTML/CSS to infer a style profile. This is intended for learning patterns
    (colors, radii, shadows) and not for copying proprietary content. Only processes user-supplied data.
    """
    try:
        content = ""
        if file is not None:
            content = (await file.read()).decode("utf-8", errors="ignore")
        elif text:
            content = text
        else:
            raise HTTPException(status_code=400, detail="Provide a file or text for analysis")

        import re

        # Extract hex/rgb(a) colors
        hex_colors = re.findall(r"#(?:[0-9a-fA-F]{3}){1,2}", content)
        rgba_colors = re.findall(r"rgba?\([^\)]+\)", content)
        colors = hex_colors + rgba_colors

        # Very naive heuristics to pick primary/secondary
        primary = next((c for c in colors if any(k in c.lower() for k in ["#22c55e", "#8b5cf6", "#22d3ee", "#60a5fa"])), None) or (colors[0] if colors else "#22d3ee")
        secondary = (colors[1] if len(colors) > 1 else None) or "#8b5cf6"

        # Radii detection
        radius_keywords = {
            "xs": ["2px", "3px"],
            "sm": ["4px", "6px"],
            "md": ["8px", "10px"],
            "lg": ["12px", "14px"],
            "xl": ["16px", "20px", "9999px", "999px", "1rem"],
        }
        radius_scale = "md"
        for scale, keys in radius_keywords.items():
            if any(k in content for k in keys):
                radius_scale = scale

        # Shadow detection
        import re as _re
        shadow_style = "neon" if _re.search(r"box-shadow:.*(0\s0\s[0-9]+px).*(inset)?", content) else "soft"

        profile = StyleProfile(
            name="analyzed",
            primary=primary,
            secondary=secondary,
            background_from="#0b0f1a",
            background_to="#0b0d16",
            neon_glow=f"rgba(34,211,238,0.65)",
            radius_scale=radius_scale,
            shadow_style=shadow_style,
        )
        notes = (
            "Profile inferred from provided content. Use responsibly and ensure you have rights to analyze the input."
        )
        return StyleAnalyzeResponse(profile=profile, notes=notes)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        from database import db

        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, "name") else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except ImportError:
        response["database"] = "❌ Database module not found"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
