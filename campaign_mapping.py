ALIADO_CAMPAÑAS = {
    "ABAI": [
        "ABAI MASIVO",
        "ABAI PROACTIVO",
        "ABAI SEGUNDO ANILLO",
        "ABAI TERCER ANILLO",
        "ABAI WHATSAPP"
    ],
    "ALMACONTACT": [
        "ALMACONTACT SWAT"
    ],
    "AQI": [
        "AQI  SEGUNDO ANILLO",
        "AQI MASIVO BARRANQUILLA",
        "AQI TERCER ANILLO",
        "AQI WHATSAPP"
    ],
    "ATENTO": [
        "ATENTO SWAT BOGOTÁ",
        "ATENTO TRASLADOS PEREIRA",
        "ATENTO PROACTIVO",
        "ATENTO  SEGUNDO ANILLO"
    ],
    "BRM": [
        "BRM FILTRO",
        "BRM MASIVO MEDELLÍN",
        "BRM TERCER ANILLO",
        "BRM WHATSAPP"
    ],
    "CLARO": [
        "ATENTO SWAT BOGOTÁ",
        "BRM FILTRO",
        "MILLENIUM MASIVO",
        "COS SEGUNDO ANILLO",
        "BRM MASIVO MEDELLÍN",
        "ATENTO TRASLADOS PEREIRA",
        "ATENTO PROACTIVO",
        "COS FIDELIZACIÓN BOGOTÁ",
        "ABAI MASIVO",
        "AQI MASIVO BARRANQUILLA",
        "COS MASIVO BOGOTÁ",
        "IBR LATAM SAC",
        "AQI WHATSAPP",
        "BRM WHATSAPP",
        "AQI  SEGUNDO ANILLO",
        "ATENTO  SEGUNDO ANILLO",
        "ALMACONTACT SWAT",
        "NEXA MASIVO",
        "ABAI SEGUNDO ANILLO",
        "ABAI PROACTIVO",
        "COS WHATSAPP",
        "MILLENIUM WEB CENTER",
        "COS RECUPERACIÓN BOGOTÁ",
        "NO EXISTE CAMPAÑA",
        "ABAI WHATSAPP",
        "ABAI TERCER ANILLO",
        "AQI TERCER ANILLO",
        "BRM TERCER ANILLO",
        "COS UPSPELLING"
    ],
    "COS": [
        "COS SEGUNDO ANILLO",
        "COS FIDELIZACIÓN BOGOTÁ",
        "COS MASIVO BOGOTÁ",
        "COS WHATSAPP",
        "COS RECUPERACIÓN BOGOTÁ",
        "COS UPSPELLING"
    ],
    "IBR LATAM": [
        "IBR LATAM SAC"
    ],
    "MILLENIUM": [
        "MILLENIUM MASIVO",
        "MILLENIUM WEB CENTER"
    ],
    "NEXA": [
        "NEXA MASIVO"
    ]
}

def get_campañas_por_aliado(aliado):
    return ALIADO_CAMPAÑAS.get(aliado.upper(), [])