import time

_groq_call_log = []


def reset_groq_tracker():
    _groq_call_log.clear()


def groq_call_tracked(groq_client, etapa: str, **kwargs):
    agora = time.time()

    if _groq_call_log:
        intervalo = agora - _groq_call_log[-1]["timestamp"]
    else:
        intervalo = None

    resultado = groq_client.chat.completions.create(**kwargs)

    entrada = {
        "n": len(_groq_call_log) + 1,
        "etapa": etapa,
        "timestamp": agora,
        "intervalo_anterior": round(intervalo, 2) if intervalo else None,
    }
    _groq_call_log.append(entrada)

    print(
        f"[Groq] chamada {entrada['n']} — {etapa} — "
        f"intervalo: {entrada['intervalo_anterior']}s"
    )

    return resultado


def log_groq_summary():
    if not _groq_call_log:
        print("[Groq] nenhuma chamada registrada")
        return
    n = len(_groq_call_log)
    print(f"[Groq] total: {n} chamadas")
    print(
        f"[Groq] janela total: "
        f"{_groq_call_log[-1]['timestamp'] - _groq_call_log[0]['timestamp']:.1f}s"
    )
    if n > 1:
        menor = min(e["intervalo_anterior"] for e in _groq_call_log[1:])
        print(f"[Groq] menor intervalo: {menor:.2f}s")
