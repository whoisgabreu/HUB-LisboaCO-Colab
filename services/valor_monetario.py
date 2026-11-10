import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def _grupos_milhar_validos(parte, separador):
    grupos = str(parte).split(separador)
    if not grupos or not re.fullmatch(r"\d{1,3}", grupos[0]):
        return False
    return all(re.fullmatch(r"\d{3}", grupo) for grupo in grupos[1:])


def parse_valor_monetario(valor, casas=2):
    quantizador = Decimal(1).scaleb(-casas)

    if valor is None:
        return Decimal("0").quantize(quantizador)
    if isinstance(valor, bool):
        raise ValueError("Valor inválido.")
    if isinstance(valor, Decimal):
        numero = valor
    elif isinstance(valor, int):
        numero = Decimal(valor)
    elif isinstance(valor, float):
        numero = Decimal(str(valor))
    else:
        texto = str(valor).replace("\u00a0", " ").strip()
        if not texto:
            return Decimal("0").quantize(quantizador)
        if "-" in texto:
            raise ValueError("Valor não pode ser negativo.")

        limpo = re.sub(r"[^\d.,]", "", texto)
        if not limpo:
            raise ValueError("Valor inválido.")

        has_dot = "." in limpo
        has_comma = "," in limpo

        if has_dot and has_comma:
            decimal_virgula = limpo.rfind(",") > limpo.rfind(".")
            sep_milhar = "." if decimal_virgula else ","
            sep_decimal = "," if decimal_virgula else "."
            corte = limpo.rfind(sep_decimal)
            parte_int = limpo[:corte]
            parte_dec = limpo[corte + 1:]

            if not re.fullmatch(r"\d{1,2}", parte_dec):
                raise ValueError("Valor inválido.")
            if sep_milhar in parte_int and not _grupos_milhar_validos(parte_int, sep_milhar):
                raise ValueError("Valor inválido.")
            if not re.fullmatch(r"\d+", parte_int.replace(sep_milhar, "")):
                raise ValueError("Valor inválido.")
            normalizado = f"{parte_int.replace(sep_milhar, '')}.{parte_dec}"
        elif has_comma:
            partes = limpo.split(",")
            ultima = partes[-1]

            if len(partes) > 2:
                if re.fullmatch(r"\d{1,2}", ultima) and _grupos_milhar_validos(",".join(partes[:-1]), ","):
                    normalizado = "".join(partes[:-1]) + "." + ultima
                elif re.fullmatch(r"\d{3}", ultima) and _grupos_milhar_validos(limpo, ","):
                    normalizado = "".join(partes)
                else:
                    raise ValueError("Valor inválido.")
            elif re.fullmatch(r"\d{1,2}", ultima):
                normalizado = f"{partes[0] or '0'}.{ultima}"
            elif re.fullmatch(r"\d{3}", ultima):
                normalizado = "".join(partes)
            else:
                raise ValueError("Valor inválido.")

            if not re.fullmatch(r"\d+(\.\d{1,2})?", normalizado):
                raise ValueError("Valor inválido.")
        elif has_dot:
            partes = limpo.split(".")
            ultima = partes[-1]

            if len(partes) > 2:
                if re.fullmatch(r"\d{1,2}", ultima) and _grupos_milhar_validos(".".join(partes[:-1]), "."):
                    normalizado = "".join(partes[:-1]) + "." + ultima
                elif re.fullmatch(r"\d{3}", ultima) and _grupos_milhar_validos(limpo, "."):
                    normalizado = "".join(partes)
                else:
                    raise ValueError("Valor inválido.")
            elif re.fullmatch(r"\d{1,2}", ultima):
                normalizado = f"{partes[0] or '0'}.{ultima}"
            elif re.fullmatch(r"\d{3}", ultima):
                normalizado = "".join(partes)
            else:
                raise ValueError("Valor inválido.")

            if not re.fullmatch(r"\d+(\.\d{1,2})?", normalizado):
                raise ValueError("Valor inválido.")
        else:
            if not re.fullmatch(r"\d+", limpo):
                raise ValueError("Valor inválido.")
            normalizado = limpo

        try:
            numero = Decimal(normalizado)
        except InvalidOperation:
            raise ValueError("Valor inválido.")

    if not numero.is_finite():
        raise ValueError("Valor inválido.")
    if numero < 0:
        raise ValueError("Valor não pode ser negativo.")
    return numero.quantize(quantizador, rounding=ROUND_HALF_UP)
