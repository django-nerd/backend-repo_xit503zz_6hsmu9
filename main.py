import os
from io import BytesIO
from typing import List, Optional, Literal

from fastapi import FastAPI, HTTPException
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


def build_design(prompt: str) -> GeneratedDesign:
    palette = infer_palette(prompt)
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
    return build_design(req.prompt)


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
        <div class=\"flex items-center gap-4\">
          <a class=\"px-5 py-3 rounded-xl glow\" style=\"background:var(--primary)\">Generate</a>
          <a class=\"px-5 py-3 rounded-xl glass\">Learn more</a>
        </div>
      </div>
      <div class=\"glass p-2 rounded-3xl\">{hero_iframe}</div>
    </section>

    <section class=\"grid lg:grid-cols-3 gap-6\">
      <div class=\"col-span-1 glass p-8 rounded-2xl\">
        <h3 class=\"text-xl mb-4\">{next((s.title for s in design.sections if s.kind=='features'), 'Features')}</h3>
        <ul class=\"space-y-3\">{features_list}</ul>
      </div>
      <div class=\"col-span-2 grid sm:grid-cols-2 gap-6\">
        <div class=\"h-48 rounded-2xl glass\"></div>
        <div class=\"h-48 rounded-2xl glow\"></div>
        <div class=\"h-48 rounded-2xl glow\"></div>
        <div class=\"h-48 rounded-2xl glass\"></div>
      </div>
    </section>

    <section class=\"glass rounded-2xl p-10 flex items-center justify-between\">
      <div>
        <h3 class=\"text-2xl font-semibold mb-2\">{next((s.title for s in design.sections if s.kind=='cta'), 'Export Instantly')}</h3>
        <p class=\"text-slate-300\">{next((s.subtitle for s in design.sections if s.kind=='cta'), '')}</p>
      </div>
      <a class=\"px-5 py-3 rounded-xl glow\" style=\"background:var(--primary)\">Download</a>
    </section>
  </main>
</body>
</html>
"""


def build_zip(design: GeneratedDesign) -> BytesIO:
    from zipfile import ZipFile, ZIP_DEFLATED

    mem = BytesIO()
    with ZipFile(mem, mode="w", compression=ZIP_DEFLATED) as z:
        z.writestr("index.html", make_index_html(design))
        # minimal README
        z.writestr(
            "README.md",
            "Generated UI package. Open index.html in a modern browser. Tailwind loaded via CDN.",
        )
    mem.seek(0)
    return mem


@app.post("/api/download")
def download(req: DownloadRequest):
    try:
        buf = build_zip(req.design)
        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=generated-ui.zip"
            },
        )
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
