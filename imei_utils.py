"""
Validation IMEI — Algorithme de Luhn
Un IMEI valide = 15 chiffres + checksum Luhn correct
"""

def validate_imei(imei: str) -> dict:
    """
    Valide un numéro IMEI.
    Retourne un dict avec is_valid et le message d'erreur si invalide.
    """
    # Nettoyer les espaces et tirets
    imei = imei.replace(" ", "").replace("-", "")

    # Vérification longueur
    if len(imei) != 15:
        return {"is_valid": False, "error": "L'IMEI doit contenir exactement 15 chiffres"}

    # Vérification que c'est bien des chiffres
    if not imei.isdigit():
        return {"is_valid": False, "error": "L'IMEI ne doit contenir que des chiffres"}

    # Algorithme de Luhn
    total = 0
    for i, digit in enumerate(imei):
        n = int(digit)
        if i % 2 == 1:          # positions paires (0-indexé) → doubler
            n *= 2
            if n > 9:
                n -= 9
        total += n

    if total % 10 != 0:
        return {"is_valid": False, "error": "Checksum IMEI invalide (algorithme de Luhn)"}

    return {"is_valid": True, "error": None}


def extract_imei_features(imei: str) -> dict:
    """
    Extrait des caractéristiques d'un IMEI pour le modèle ML.
    Le TAC (6 premiers chiffres) identifie le fabricant/modèle.
    """
    tac    = imei[:6]   # Type Allocation Code — identifie le modèle
    snr    = imei[6:14] # Serial Number — numéro de série
    check  = imei[14]   # Check digit

    return {
        "tac":          int(tac),
        "tac_prefix":   int(tac[:2]),   # 2 premiers = région/fabricant
        "snr_numeric":  int(snr),
        "check_digit":  int(check),
        "imei_sum":     sum(int(d) for d in imei),
        "imei_variance": _digit_variance(imei),
    }


def _digit_variance(imei: str) -> float:
    """Variance des chiffres — utile pour détecter des IMEI suspects."""
    digits = [int(d) for d in imei]
    mean   = sum(digits) / len(digits)
    return sum((d - mean) ** 2 for d in digits) / len(digits)
