from scripts.affiliate.opportunity_engine import analyze_opportunity


analise = {
    "score": 92,
    "potencial": "alto"
}

score_tecnico = {
    "score": 85
}


resultado = analyze_opportunity(
    analise,
    score_tecnico
)

print(resultado)
