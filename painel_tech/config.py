import copy
import json
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "prioridade": {
        "pesos": {"impacto": 0.35, "urgencia": 0.30, "risco": 0.20, "esforco": 0.15},
        "bandas": {"critica": 3.3, "alta": 2.6, "media": 1.9},
    },
    "capacidade": {"limite_ativo_padrao": 3},
    "agenda": {
        "dias": ["seg", "ter", "qua", "qui", "sex"],
        "expediente": {"inicio": "09:00", "fim": "18:00"},
        "almoco": {"inicio": "12:00", "fim": "13:00"},
        "slot_min": 30,
        "horas_por_esforco": {
            "pequeno": 2,
            "medio": 4,
            "grande": 8,
            "muito_grande": 14,
        },
    },
    "saude": {
        "limiares_ritmo": [
            {"min": 0.25, "ritmo": "muito_rapido"},
            {"min": 0.10, "ritmo": "rapido"},
            {"min": -0.10, "ritmo": "fluindo"},
            {"min": -0.25, "ritmo": "lento"},
        ],
        "dias_bloqueio_alerta": 3,
        "dias_sem_movimento": 7,
    },
    "regras": [
        {
            "id": "urgencia_alta_ritmo_lento",
            "severidade": "atencao",
            "icone": "⚠️",
            "mensagem": "Alinhamento necessário",
            "quando": {"urgencia": {"min": 3}, "ritmo": {"in": ["lento", "muito_lento"]}},
        },
        {
            "id": "risco_alto_ritmo_lento",
            "severidade": "critico",
            "icone": "🚨",
            "mensagem": "Intervenção imediata",
            "quando": {"risco": {"min": 3}, "ritmo": {"in": ["lento", "muito_lento"]}},
        },
        {
            "id": "prioridade_maxima",
            "severidade": "info",
            "icone": "🔥",
            "mensagem": "Prioridade máxima",
            "quando": {
                "impacto": {"min": 3},
                "urgencia": {"min": 3},
                "ritmo": {"in": ["fluindo", "rapido", "muito_rapido"]},
            },
        },
        {
            "id": "esforco_alto_impacto_baixo",
            "severidade": "info",
            "icone": "💡",
            "mensagem": "Avaliar se vale continuar",
            "quando": {"esforco": {"min": 3}, "impacto": {"max": 1}},
        },
        {
            "id": "muito_rapido_esforco_alto",
            "severidade": "atencao",
            "icone": "👀",
            "mensagem": "Verificar qualidade / sustentabilidade",
            "quando": {"ritmo": {"in": ["muito_rapido"]}, "esforco": {"min": 3}},
        },
        {
            "id": "bloqueio_prolongado",
            "severidade": "critico",
            "icone": "🚨",
            "mensagem": "Bloqueio prolongado",
            "quando": {"bloqueio_dias": {"min": 3}},
        },
        {
            "id": "projeto_parado",
            "severidade": "atencao",
            "icone": "⚠️",
            "mensagem": "Projeto sem movimento",
            "quando": {"dias_sem_movimento": {"min": 7}, "status": {"in": ["ativo"]}},
        },
        {
            "id": "etapa_vencida",
            "severidade": "atencao",
            "icone": "⏰",
            "mensagem": "Etapa vencida",
            "quando": {"etapas_vencidas": {"min": 1}},
        },
        {
            "id": "etapa_vencida_multipla",
            "severidade": "critico",
            "icone": "🚨",
            "mensagem": "Muitas etapas vencidas",
            "quando": {"etapas_vencidas": {"min": 3}},
        },
        {
            "id": "dependencia_pendente",
            "severidade": "atencao",
            "icone": "⛓️",
            "mensagem": "Etapa aguardando dependência",
            "quando": {"dependencias_bloqueadas": {"min": 1}},
        },
    ],
}


def _merge(base, override):
    for chave, valor in override.items():
        if isinstance(valor, dict) and isinstance(base.get(chave), dict):
            base[chave] = _merge(base[chave], valor)
        else:
            base[chave] = valor
    return base


def get_config():
    if not os.path.exists(CONFIG_PATH):
        return copy.deepcopy(DEFAULT_CONFIG)
    with open(CONFIG_PATH, encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    return _merge(copy.deepcopy(DEFAULT_CONFIG), dados)


def save_config(dados):
    with open(CONFIG_PATH, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)


def validar_config(dados):
    erros = []
    if not isinstance(dados, dict):
        return ["A configuração deve ser um objeto JSON."]

    prioridade = dados.get("prioridade", {})
    if not isinstance(prioridade, dict):
        erros.append("'prioridade' deve ser um objeto.")
    else:
        pesos = prioridade.get("pesos", {})
        if not isinstance(pesos, dict) or not pesos:
            erros.append("'prioridade.pesos' deve ser um objeto com pesos.")
        else:
            numericos = [v for v in pesos.values() if isinstance(v, (int, float))]
            for chave, valor in pesos.items():
                if not isinstance(valor, (int, float)) or isinstance(valor, bool) or valor < 0:
                    erros.append(f"Peso '{chave}' deve ser um número ≥ 0.")
            if numericos and sum(numericos) <= 0:
                erros.append("A soma dos pesos deve ser maior que zero.")

        bandas = prioridade.get("bandas", {})
        if not isinstance(bandas, dict):
            erros.append("'prioridade.bandas' deve ser um objeto.")
        else:
            valores = [bandas.get(c) for c in ("critica", "alta", "media")]
            if not all(isinstance(v, (int, float)) for v in valores):
                erros.append("Bandas 'critica', 'alta' e 'media' devem ser numéricas.")
            elif not (valores[0] >= valores[1] >= valores[2]):
                erros.append("Bandas devem estar em ordem: critica ≥ alta ≥ media.")

    saude = dados.get("saude", {})
    if not isinstance(saude, dict):
        erros.append("'saude' deve ser um objeto.")
    elif "limiares_ritmo" in saude and not isinstance(saude["limiares_ritmo"], list):
        erros.append("'saude.limiares_ritmo' deve ser uma lista.")

    if "regras" in dados and not isinstance(dados["regras"], list):
        erros.append("'regras' deve ser uma lista.")

    capacidade = dados.get("capacidade", {})
    if not isinstance(capacidade, dict):
        erros.append("'capacidade' deve ser um objeto.")
    else:
        limite = capacidade.get("limite_ativo_padrao")
        if limite is not None and (
            not isinstance(limite, (int, float))
            or isinstance(limite, bool)
            or limite < 0
        ):
            erros.append("'capacidade.limite_ativo_padrao' deve ser um número ≥ 0.")

    _validar_agenda(dados.get("agenda", {}), erros)

    return erros


def _hora_valida(texto):
    if not isinstance(texto, str) or ":" not in texto:
        return False
    partes = texto.split(":")
    if len(partes) != 2:
        return False
    try:
        hora, minuto = int(partes[0]), int(partes[1])
    except ValueError:
        return False
    return 0 <= hora <= 23 and 0 <= minuto <= 59


def _validar_agenda(agenda, erros):
    if not isinstance(agenda, dict):
        erros.append("'agenda' deve ser um objeto.")
        return

    dias = agenda.get("dias")
    if dias is not None and not isinstance(dias, list):
        erros.append("'agenda.dias' deve ser uma lista.")

    slot = agenda.get("slot_min")
    if slot is not None and (
        not isinstance(slot, int) or isinstance(slot, bool) or slot <= 0
    ):
        erros.append("'agenda.slot_min' deve ser um inteiro > 0.")

    for nome in ("expediente", "almoco"):
        faixa = agenda.get(nome, {})
        if not isinstance(faixa, dict):
            erros.append(f"'agenda.{nome}' deve ser um objeto.")
            continue
        for rotulo in ("inicio", "fim"):
            valor = faixa.get(rotulo)
            if valor is not None and not _hora_valida(valor):
                erros.append(
                    f"'agenda.{nome}.{rotulo}' deve ser um horário HH:MM."
                )
        if (
            _hora_valida(faixa.get("inicio"))
            and _hora_valida(faixa.get("fim"))
            and faixa["fim"] <= faixa["inicio"]
        ):
            erros.append(f"'agenda.{nome}.fim' deve ser depois de 'inicio'.")

    horas = agenda.get("horas_por_esforco", {})
    if not isinstance(horas, dict):
        erros.append("'agenda.horas_por_esforco' deve ser um objeto.")
    else:
        for chave, valor in horas.items():
            if (
                not isinstance(valor, (int, float))
                or isinstance(valor, bool)
                or valor <= 0
            ):
                erros.append(
                    f"'agenda.horas_por_esforco.{chave}' deve ser um número > 0."
                )



def reset_config():
    save_config(copy.deepcopy(DEFAULT_CONFIG))
    return get_config()
