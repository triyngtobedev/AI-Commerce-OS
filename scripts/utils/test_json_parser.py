from json_parser import parse_json_response


resposta_ia = """
```json
{
  "score": 92,
  "potencial": "alto"
}
"""

resultado = parse_json_response(resposta_ia)

print(resultado)
print(resultado["score"])