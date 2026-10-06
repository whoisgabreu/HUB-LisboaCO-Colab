"""Normalização de nomes de grupo para exibição no dashboard.

Remove os conectores de marca ("V4 Company &", "& V4 Company", "V4 Company +",
"+ V4 Company") para encurtar e facilitar a identificação do cliente.
Não altera a fonte/banco de dados — apenas o valor usado pelo dashboard.
"""

import re

_PADROES = (
    r"\s*[&+]\s*v4\s*company\s*",   # "& V4 Company" / "+ V4 company"
    r"\s*v4\s*company\s*[&+]\s*",   # "V4 Company &" / "V4 company +"
)


def limpar_nome_grupo(nome):
    """Remove os conectores de marca do nome do grupo (case-insensitive).

    Se o resultado ficar vazio, devolve o nome original.
    """
    if not nome:
        return nome

    s = str(nome)
    anterior = None
    while s != anterior:
        anterior = s
        for padrao in _PADROES:
            s = re.sub(padrao, " ", s, flags=re.IGNORECASE)

    s = re.sub(r"\s+", " ", s).strip(" &+").strip()
    return s or nome
