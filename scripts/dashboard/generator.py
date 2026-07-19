"""
Dashboard generator — ai-commerce-os.

Gera output/dashboard.json e output/dashboard.html com:
  - Jobs Railway (pipeline_jobs.db)
  - Analytics YouTube (database/analytics.json)
  - Status n8n (via HTTP se N8N_URL configurado)
  - Relatórios semanais (reports/)

Uso:
  python scripts/dashboard/generator.py
  python scripts/dashboard/generator.py --open
  python scripts/dashboard/generator.py --watch
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)

ANALYTICS_FILE = ROOT / "database" / "analytics.json"
VIDEOS_FILE = ROOT / "database" / "videos.json"
REPORTS_DIR = ROOT / "reports"
DB_PATH = Path(os.getenv("DATABASE_PATH", str(ROOT / "database" / "pipeline_jobs.db")))
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")


def generate_dashboard(results: list[dict]) -> dict:
    """Compatível com product_pipeline — dashboard de produtos."""
    dashboard = {
        "atualizado_em": datetime.now().isoformat(),
        "produtos": [],
    }
    for item in results:
        dashboard["produtos"].append(
            {
                "nome": item["produto"]["nome"],
                "score": item["oportunidade"]["score_venda"],
                "acao": item["acao"],
            }
        )

    json_path = OUTPUT / "dashboard.json"
    json_path.write_text(json.dumps(dashboard, ensure_ascii=False, indent=4), encoding="utf-8")
    return dashboard


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def collect_jobs() -> dict:
    if not DB_PATH.exists():
        return {"error": "database não encontrado", "jobs": [], "summary": {}}

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(
            """
            SELECT job_id, status, topic, template, created_at, updated_at,
                   stdout_tail, error_message
            FROM pipeline_jobs
            ORDER BY created_at DESC
            LIMIT 50
            """
        )
        jobs = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT status, COUNT(*) as count FROM pipeline_jobs GROUP BY status")
        summary = {r["status"]: r["count"] for r in cur.fetchall()}

        cur.execute("SELECT COUNT(*) as total FROM pipeline_jobs")
        summary["total"] = cur.fetchone()["total"]

        conn.close()
        return {"jobs": jobs, "summary": summary, "db_path": str(DB_PATH)}
    except Exception as exc:
        return {"error": str(exc), "jobs": [], "summary": {}}


def collect_analytics() -> dict:
    if not ANALYTICS_FILE.exists():
        return {"error": "analytics.json não encontrado", "videos": []}

    try:
        data = json.loads(ANALYTICS_FILE.read_text(encoding="utf-8"))
        return {
            "videos": data if isinstance(data, list) else data.get("videos", []),
            "raw": data,
        }
    except Exception as exc:
        return {"error": str(exc), "videos": []}


def collect_videos() -> dict:
    if not VIDEOS_FILE.exists():
        return {"videos": []}
    try:
        data = json.loads(VIDEOS_FILE.read_text(encoding="utf-8"))
        videos = data if isinstance(data, list) else data.get("videos", [])
        return {"videos": videos, "total": len(videos)}
    except Exception as exc:
        return {"error": str(exc), "videos": []}


def collect_reports() -> dict:
    if not REPORTS_DIR.exists():
        return {"reports": []}
    reports = []
    for f in sorted(REPORTS_DIR.glob("relatorio_*.md"), reverse=True)[:10]:
        stat = f.stat()
        reports.append(
            {
                "filename": f.name,
                "path": str(f),
                "size_kb": round(stat.st_size / 1024, 1),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        )
    return {"reports": reports}


def collect_n8n_status() -> dict:
    try:
        import urllib.request

        req = urllib.request.Request(f"{N8N_URL}/healthz")
        with urllib.request.urlopen(req, timeout=5) as r:
            return {"status": "running", "url": N8N_URL, "http_status": r.status}
    except Exception as exc:
        return {"status": "offline", "url": N8N_URL, "error": str(exc)}


def build_dashboard_data() -> dict:
    print("Coletando dados...")
    jobs_data = collect_jobs()
    analytics_data = collect_analytics()
    videos_data = collect_videos()
    reports_data = collect_reports()
    n8n_data = collect_n8n_status()

    summary = jobs_data.get("summary", {})
    videos = videos_data.get("videos", [])
    total_views = sum(v.get("views", 0) for v in analytics_data.get("videos", []))

    return {
        "generated_at": now_iso(),
        "metrics": {
            "jobs_total": summary.get("total", 0),
            "jobs_completed": summary.get("completed", 0),
            "jobs_failed": summary.get("failed", summary.get("error", 0)),
            "jobs_running": summary.get("running", summary.get("processing", 0)),
            "videos_published": len(videos),
            "total_views": total_views,
            "reports_generated": len(reports_data.get("reports", [])),
            "n8n_status": n8n_data.get("status", "unknown"),
        },
        "jobs": jobs_data,
        "analytics": analytics_data,
        "videos": videos_data,
        "reports": reports_data,
        "n8n": n8n_data,
    }


def generate_html(data: dict) -> str:
    m = data["metrics"]
    jobs = data["jobs"].get("jobs", [])[:10]
    videos = data["videos"].get("videos", [])[:8]
    reports = data["reports"].get("reports", [])[:5]
    n8n = data["n8n"]
    gen = data["generated_at"]

    def status_badge(status: str) -> str:
        colors = {
            "completed": "#1D9E75",
            "failed": "#E24B4A",
            "error": "#E24B4A",
            "running": "#378ADD",
            "processing": "#378ADD",
            "pending": "#BA7517",
            "queued": "#BA7517",
        }
        color = colors.get(status, "#888780")
        return (
            f'<span style="background:{color};color:#fff;font-size:11px;'
            f'padding:2px 8px;border-radius:4px;font-weight:500">{status}</span>'
        )

    jobs_rows = ""
    for job in jobs:
        ts = (job.get("created_at") or "")[:16].replace("T", " ")
        jobs_rows += f"""
        <tr>
          <td style="font-family:monospace;font-size:12px;color:#378ADD">{(job.get('job_id') or '')[:12]}…</td>
          <td>{status_badge(job.get('status','?'))}</td>
          <td style="font-size:13px">{job.get('topic','—')[:40]}</td>
          <td style="font-size:12px;color:#888">{job.get('template','—')}</td>
          <td style="font-size:12px;color:#888">{ts}</td>
        </tr>"""

    video_cards = ""
    for video in videos:
        video_cards += f"""
        <div style="background:#f9f9f8;border:0.5px solid #e0e0dc;border-radius:8px;padding:12px">
          <p style="font-size:13px;font-weight:500;margin:0 0 6px">{video.get('title','Sem título')[:50]}</p>
          <p style="font-size:12px;color:#888;margin:0">{video.get('views',0):,} views · {video.get('likes',0):,} likes</p>
          <p style="font-size:11px;color:#aaa;margin:4px 0 0">{(video.get('published_at',''))[:10]}</p>
        </div>"""

    report_items = ""
    for report in reports:
        report_items += f"""
        <li style="font-size:13px;padding:6px 0;border-bottom:0.5px solid #eee">
          📄 {report['filename']} <span style="color:#aaa;font-size:11px">({report['size_kb']} KB)</span>
        </li>"""

    n8n_color = "#1D9E75" if n8n.get("status") == "running" else "#E24B4A"
    n8n_label = "rodando" if n8n.get("status") == "running" else "offline"

    jobs_section = (
        f'<p style="color:#aaa;font-size:13px">{data["jobs"].get("error","")}</p>'
        if data["jobs"].get("error")
        else (
            f"""
    <table>
      <thead><tr>
        <th>Job ID</th><th>Status</th><th>Tópico</th><th>Template</th><th>Criado em</th>
      </tr></thead>
      <tbody>{jobs_rows}</tbody>
    </table>"""
            if jobs_rows
            else '<p style="color:#aaa;font-size:13px">Nenhum job encontrado.</p>'
        )
    )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ai-commerce-os — Dashboard</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f4f3f0; color: #1a1a1a; }}
  .header {{ background: #1a1a1a; color: #fff; padding: 20px 32px; display: flex; align-items: center; justify-content: space-between; }}
  .header h1 {{ font-size: 18px; font-weight: 500; }}
  .header span {{ font-size: 12px; color: #888; }}
  .content {{ max-width: 1100px; margin: 0 auto; padding: 24px 16px; }}
  .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 24px; }}
  .metric {{ background: #fff; border-radius: 8px; padding: 16px; border: 0.5px solid #e0e0dc; }}
  .metric-val {{ font-size: 26px; font-weight: 500; }}
  .metric-lbl {{ font-size: 12px; color: #888; margin-top: 4px; }}
  .card {{ background: #fff; border-radius: 12px; border: 0.5px solid #e0e0dc; padding: 20px; margin-bottom: 16px; }}
  .card h2 {{ font-size: 15px; font-weight: 500; margin-bottom: 16px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; color: #888; font-size: 11px; font-weight: 500; padding: 0 0 8px; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 0.5px solid #eee; }}
  td {{ padding: 8px 0; border-bottom: 0.5px solid #f5f5f3; vertical-align: middle; }}
  tr:last-child td {{ border-bottom: none; }}
  .video-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; }}
  .refresh-btn {{ background: #1a1a1a; color: #fff; border: none; border-radius: 6px; padding: 8px 16px; font-size: 13px; cursor: pointer; }}
  .refresh-btn:hover {{ background: #333; }}
</style>
</head>
<body>

<div class="header">
  <h1>ai-commerce-os</h1>
  <div style="display:flex;align-items:center;gap:16px">
    <span style="color:{n8n_color}">● n8n {n8n_label}</span>
    <span>Atualizado: {gen[:16].replace('T',' ')} UTC</span>
    <button class="refresh-btn" onclick="location.reload()">Atualizar</button>
  </div>
</div>

<div class="content">
  <div class="metrics">
    <div class="metric"><div class="metric-val">{m['jobs_total']}</div><div class="metric-lbl">Jobs totais</div></div>
    <div class="metric"><div class="metric-val" style="color:#1D9E75">{m['jobs_completed']}</div><div class="metric-lbl">Concluídos</div></div>
    <div class="metric"><div class="metric-val" style="color:#E24B4A">{m['jobs_failed']}</div><div class="metric-lbl">Com falha</div></div>
    <div class="metric"><div class="metric-val" style="color:#378ADD">{m['jobs_running']}</div><div class="metric-lbl">Em execução</div></div>
    <div class="metric"><div class="metric-val">{m['videos_published']}</div><div class="metric-lbl">Vídeos publicados</div></div>
    <div class="metric"><div class="metric-val">{m['total_views']:,}</div><div class="metric-lbl">Views totais</div></div>
  </div>

  <div class="card">
    <h2>Jobs recentes (Railway)</h2>
    {jobs_section}
  </div>

  <div class="card">
    <h2>Vídeos publicados</h2>
    {f'<div class="video-grid">{video_cards}</div>' if video_cards else '<p style="color:#aaa;font-size:13px">Nenhum vídeo registrado ainda.</p>'}
  </div>

  <div class="card">
    <h2>Relatórios semanais</h2>
    {f'<ul style="list-style:none">{report_items}</ul>' if report_items else '<p style="color:#aaa;font-size:13px">Nenhum relatório gerado ainda.</p>'}
  </div>
</div>
</body>
</html>"""


def generate(open_browser: bool = False) -> None:
    data = build_dashboard_data()

    json_path = OUTPUT / "dashboard.json"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  JSON: {json_path}")

    html_path = OUTPUT / "dashboard.html"
    html_path.write_text(generate_html(data), encoding="utf-8")
    print(f"  HTML: {html_path}")

    metrics = data["metrics"]
    print(
        f"\n  Jobs: {metrics['jobs_completed']} ok / {metrics['jobs_failed']} falha / "
        f"{metrics['jobs_running']} rodando"
    )
    print(f"  Vídeos publicados: {metrics['videos_published']} | Views: {metrics['total_views']:,}")
    print(f"  n8n: {metrics['n8n_status']}")

    if open_browser:
        webbrowser.open(html_path.as_uri())


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera dashboard do ai-commerce-os")
    parser.add_argument("--open", action="store_true", help="Abrir no browser após gerar")
    parser.add_argument("--watch", action="store_true", help="Atualizar a cada 60 segundos")
    args = parser.parse_args()

    if args.watch:
        print("Modo watch ativado (Ctrl+C para parar)\n")
        while True:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Gerando dashboard...")
            generate(open_browser=False)
            time.sleep(60)
    else:
        generate(open_browser=args.open)


if __name__ == "__main__":
    main()
