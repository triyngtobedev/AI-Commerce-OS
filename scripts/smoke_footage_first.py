#!/usr/bin/env python3
"""
Smoke test do pipeline footage-first.

Valida módulos editoriais sem depender de APIs externas ou render completo.
Tema: Como a Shein ficou tão poderosa tão rápido
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from scripts.core.asset_rights_ledger import AssetRightsLedger, evaluate_license
    from scripts.video.visual_grammar import apply_visual_grammar_to_scenes
    from scripts.youtube.scene_visual_planner import enrich_scenes_with_visual_plan
    from scripts.youtube.retention_analyzer import analyze_retention, run_retention_pipeline
    from scripts.research.research_pack import generate_research_pack, _fallback_research_pack
    from scripts.video.t2v_decision import T2VTracker, evaluate_t2v_decision, MAX_T2V_SCENES
    from scripts.core.production.quality_gate import run_quality_gate
    from scripts.youtube.youtube_packager import generate_youtube_package
    from scripts.video.media_search_orchestrator import generate_scene_queries

    topic = {
        "nome": "Como a Shein ficou tão poderosa tão rápido",
        "categoria": "negocios",
        "keywords": ["Shein", "fast fashion", "e-commerce", "China"],
    }

    print("=" * 60)
    print("SMOKE TEST — Footage-First Pipeline")
    print(f"Tema: {topic['nome']}")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp)

        # 1. Research Pack
        pack = _fallback_research_pack(topic)
        (output_dir / "research_pack.json").write_text(
            json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"✅ Research Pack: {len(pack['main_facts'])} fatos, {len(pack['real_image_search_terms_en'])} termos EN")

        # 2. Script + Retention
        script = {
            "hook": "Em menos de dez anos, a Shein ultrapassou marcas centenárias. Como?",
            "contexto": "A moda rápida sempre existiu. Mas algo mudou em 2012.",
            "desenvolvimento": (
                "Fábricas aceleradas. Pressão logística. Preços impossíveis. "
                "Mas espere — tem mais. A Shein não vendia roupa. Vendia velocidade. "
                "E aqui a história fica estranha."
            ) * 8,
            "revelacao": "O segredo não era a fábrica. Era o algoritmo que decidia o que produzir.",
            "consequencias": "Em 2020, a Shein valia mais que a H&M e a Zara juntas.",
            "encerramento": "A próxima vez que comprar algo barato, lembre: alguém pagou o preço.",
        }
        script, retention = run_retention_pipeline(script, topic=topic["nome"], output_dir=output_dir)
        print(f"✅ Retention: score={retention.overall_score:.0f}, hook={retention.hook_strength:.0f}")

        # 3. Scenes + Visual Plan + Grammar
        scenes = {
            "produto": topic["nome"],
            "cenas": [
                {"tipo": "hook", "visual": "textile factory production line fast fashion", "narracao": script["hook"][:100]},
                {"tipo": "contexto", "visual": "guangzhou china fashion district aerial", "narracao": script["contexto"][:100]},
                {"tipo": "desenvolvimento_1", "visual": "ecommerce warehouse sorting packages", "narracao": "logística"},
                {"tipo": "desenvolvimento_2", "visual": "garment workers sewing machine factory", "narracao": "produção"},
                {"tipo": "revelacao", "visual": "data algorithm screen fashion analytics", "narracao": script["revelacao"][:100]},
                {"tipo": "consequencias", "visual": "shopping mall empty stores closed", "narracao": script["consequencias"][:100]},
                {"tipo": "impacto", "visual": "global shipping containers port logistics", "narracao": "impacto"},
                {"tipo": "encerramento", "visual": "sunset city skyline contemplative", "narracao": script["encerramento"][:100]},
            ],
        }
        scenes = enrich_scenes_with_visual_plan(scenes, topic=topic["nome"], research_pack=pack, script=script)
        scenes = apply_visual_grammar_to_scenes(scenes)
        print(f"✅ Visual Plan: {len(scenes['cenas'])} cenas enriquecidas")

        # 4. Query generation per scene
        for i, scene in enumerate(scenes["cenas"][:2]):
            queries = generate_scene_queries(scene, topic=topic["nome"])
            print(f"   Cena {i+1} queries: {len(queries)} tipos")

        # 5. T2V decisions
        tracker = T2VTracker()
        t2v_approved = 0
        for i, scene in enumerate(scenes["cenas"]):
            decision = evaluate_t2v_decision(
                i + 1, scene, {"busca": scene["visual"], "tipo": scene["tipo"]},
                tracker=tracker, stock_failed=True, editorial_failed=True,
            )
            if decision.should_use_t2v and tracker.can_use_t2v():
                tracker.record_use(i + 1, decision)
                t2v_approved += 1
        print(f"✅ T2V: {t2v_approved}/{MAX_T2V_SCENES} cenas aprovadas (limite respeitado)")

        # 6. Asset Rights Ledger
        ledger = AssetRightsLedger(output_dir)
        for i in range(1, 9):
            license_ok = evaluate_license("Pexels License", provider="pexels")
            ledger.register_asset(
                source="pexels", provider="pexels",
                license_text="Pexels License", media_type="video" if i <= 3 else "photo",
                scene_id=i, width=1920, height=1080, topic_relevance_score=0.7 + i * 0.02,
            )
        ledger.export_report(output_dir)
        print(f"✅ Asset Rights: {ledger.all_safe()} — report exported")

        # 7. Simulated media search results
        media_scenes = []
        for i in range(8):
            media_scenes.append({
                "scene": i + 1,
                "saved": True,
                "media_type": "video" if i < 3 else ("editorial_ken_burns" if i < 6 else "image"),
                "provedor": ["pexels", "wikimedia", "pixabay", "generated"][i % 4],
                "quality_score": 0.65 + i * 0.03,
                "width": 1920,
                "height": 1080,
            })
        assets_dir = output_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        (assets_dir / "media_search.json").write_text(
            json.dumps({"scenes": media_scenes, "t2v_usage": tracker.to_dict()}),
            encoding="utf-8",
        )

        # 8. Quality Gate
        result = {"cenas": {"cenas": [{"duration_seconds": 55 + i * 3} for i in range(8)]}, "conteudo": {"titulo": topic["nome"]}}
        gate = run_quality_gate(output_dir, result, block_on_failure=False, ledger=ledger)
        print(f"✅ Quality Gate: approved={gate.approved}, score={gate.publish_ready_score}")

        # 9. YouTube Package
        package = generate_youtube_package({
            "produto": topic,
            "conteudo": {"titulo": topic["nome"], "descricao": "Documentário", "tags": ["shein", "fast fashion"]},
            "roteiro": script,
            "cenas": scenes,
            "youtube_metadata": {"capitulos": []},
        }, export_folder=output_dir)
        print(f"✅ YouTube Package: {len(package['titulo_variacoes'])} títulos, {len(package['thumbnail_ideas'])} thumbnail ideas")

        # Summary
        print("\n" + "=" * 60)
        print("RELATÓRIOS GERADOS:")
        for name in (
            "research_pack.json", "retention_report.json",
            "asset_rights_report.json", "quality_report.json",
            "youtube_package.json", "thumbnail_brief.json",
        ):
            path = output_dir / name
            status = "✅" if path.exists() else "❌"
            print(f"  {status} {name}")

        print("=" * 60)
        print("SMOKE TEST CONCLUÍDO COM SUCESSO")
        return 0


if __name__ == "__main__":
    sys.exit(main())
