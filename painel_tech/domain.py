STATUS = {
    "fila": {"label": "Na fila", "cor": "ambar", "emoji": "🟡"},
    "ativo": {"label": "Ativo", "cor": "azul", "emoji": "🔵"},
    "pausado": {"label": "Pausado", "cor": "cinza", "emoji": "⚪"},
    "finalizado": {"label": "Finalizado", "cor": "verde", "emoji": "🟢"},
}

IMPACTO = {
    "baixo": {"nivel": 1, "label": "Baixo", "cor": "verde", "emoji": "🟢"},
    "medio": {"nivel": 2, "label": "Médio", "cor": "ambar", "emoji": "🟡"},
    "alto": {"nivel": 3, "label": "Alto", "cor": "laranja", "emoji": "🟠"},
    "critico": {"nivel": 4, "label": "Crítico", "cor": "vermelho", "emoji": "🔴"},
}

URGENCIA = {
    "baixa": {"nivel": 1, "label": "Baixa", "cor": "verde", "emoji": "🟢"},
    "media": {"nivel": 2, "label": "Média", "cor": "ambar", "emoji": "🟡"},
    "alta": {"nivel": 3, "label": "Alta", "cor": "laranja", "emoji": "🟠"},
    "critica": {"nivel": 4, "label": "Crítica", "cor": "vermelho", "emoji": "🔴"},
}

RISCO = {
    "baixo": {"nivel": 1, "label": "Baixo", "cor": "verde", "emoji": "🟢"},
    "medio": {"nivel": 2, "label": "Médio", "cor": "ambar", "emoji": "🟡"},
    "alto": {"nivel": 3, "label": "Alto", "cor": "laranja", "emoji": "🟠"},
    "critico": {"nivel": 4, "label": "Crítico", "cor": "vermelho", "emoji": "🔴"},
}

ESFORCO = {
    "pequeno": {"nivel": 1, "label": "Pequeno", "cor": "verde", "emoji": "🟢"},
    "medio": {"nivel": 2, "label": "Médio", "cor": "ambar", "emoji": "🟡"},
    "grande": {"nivel": 3, "label": "Grande", "cor": "laranja", "emoji": "🟠"},
    "muito_grande": {"nivel": 4, "label": "Muito grande", "cor": "vermelho", "emoji": "🔴"},
}

INDICADORES = {
    "impacto": {"label": "Impacto", "opcoes": IMPACTO},
    "urgencia": {"label": "Urgência", "opcoes": URGENCIA},
    "risco": {"label": "Risco", "opcoes": RISCO},
    "esforco": {"label": "Esforço", "opcoes": ESFORCO},
}

RITMO = {
    "muito_lento": {"nivel": 1, "label": "Muito lento", "cor": "vermelho", "emoji": "🔴"},
    "lento": {"nivel": 2, "label": "Lento", "cor": "laranja", "emoji": "🟠"},
    "fluindo": {"nivel": 3, "label": "Fluindo", "cor": "verde", "emoji": "🟢"},
    "rapido": {"nivel": 4, "label": "Rápido", "cor": "azul", "emoji": "🔵"},
    "muito_rapido": {"nivel": 5, "label": "Muito rápido", "cor": "azul", "emoji": "🔷"},
}

PRIORIDADE = {
    "critica": {"label": "Crítica", "cor": "vermelho", "emoji": "🔴"},
    "alta": {"label": "Alta", "cor": "laranja", "emoji": "🔥"},
    "media": {"label": "Média", "cor": "ambar", "emoji": "🟡"},
    "baixa": {"label": "Baixa", "cor": "cinza", "emoji": "⚪"},
}

INTERVENCAO = {
    "intervencao": {"label": "Intervenção necessária", "cor": "vermelho", "emoji": "🚨"},
    "atencao": {"label": "Atenção", "cor": "ambar", "emoji": "⚠️"},
    "normal": {"label": "Normal", "cor": "verde", "emoji": "✅"},
}

ETAPA_STATUS = {
    "pendente": {"label": "Pendente", "cor": "cinza", "emoji": "☐"},
    "em_andamento": {"label": "Em andamento", "cor": "azul", "emoji": "🔄"},
    "concluida": {"label": "Concluída", "cor": "verde", "emoji": "☑"},
}

SEVERIDADE_COR = {"info": "azul", "atencao": "ambar", "critico": "vermelho"}


def _tabela(campo):
    return RITMO if campo == "ritmo" else INDICADORES[campo]["opcoes"]


def meta_indicador(campo, valor):
    return _tabela(campo).get(
        valor, {"nivel": 0, "label": valor or "", "cor": "cinza", "emoji": ""}
    )


def nivel_indicador(campo, valor):
    return meta_indicador(campo, valor)["nivel"]


def label_indicador(campo, valor):
    return meta_indicador(campo, valor)["label"]


def cor_indicador(campo, valor):
    return meta_indicador(campo, valor)["cor"]


def emoji_indicador(campo, valor):
    return meta_indicador(campo, valor)["emoji"]


def opcoes(campo):
    return _tabela(campo)


def label_status(valor):
    return STATUS.get(valor, {"label": valor or "", "cor": "cinza", "emoji": ""})


def label_prioridade(valor):
    return PRIORIDADE.get(valor, {"label": valor or "", "cor": "cinza", "emoji": ""})


def label_ritmo(valor):
    return RITMO.get(valor, {"label": valor or "", "cor": "cinza", "emoji": ""})


def label_intervencao(valor):
    return INTERVENCAO.get(valor, {"label": valor or "", "cor": "cinza", "emoji": ""})


def label_etapa_status(valor):
    return ETAPA_STATUS.get(valor, {"label": valor or "", "cor": "cinza", "emoji": ""})
