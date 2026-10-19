# Entrypoint para servicio interno centro_operaciones en Vercel
def handler(request, context=None):
    return {"status": "ok", "service": "centro_operaciones"}
