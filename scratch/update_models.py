import sys

with open('models.py', 'r') as f:
    lines = f.readlines()

new_class = [
    '\n',
    'class Projeto(Base):\n',
    '    """Tabela unificada: plataforma_geral.projetos"""\n',
    '    __tablename__ = "projetos"\n',
    '    __table_args__ = {"schema": "plataforma_geral"}\n',
    '\n',
    '    pipefy_id = Column(Integer, primary_key=True)\n',
    '    id = Column(Integer)\n',
    '    nome = Column(String(250))\n',
    '    documento = Column(String(250))\n',
    '    fee = Column(DECIMAL(15, 2))\n',
    '    moeda = Column(String(6))\n',
    '    squad_atribuida = Column(String(20))\n',
    '    produto_contratado = Column(String(250))\n',
    '    data_de_inicio = Column(Date)\n',
    '    cohort = Column(String(100))\n',
    '    meta_account_id = Column(String(100))\n',
    '    google_account_id = Column(String(100))\n',
    '    fase_do_pipefy = Column(String(100))\n',
    '    url_webhook_gchat = Column(String(250))\n',
    '    step = Column(String(15))\n',
    '    informacoes_gerais = Column(String(1500))\n',
    '    orcamento_midia_meta = Column(Integer)\n',
    '    orcamento_midia_google = Column(Integer)\n',
    '    data_fim = Column(Date)\n',
    '    extra = Column(JSONB)\n',
    '    notas = Column(JSONB)\n',
    '    ekyte_workspace = Column(String(2500))\n',
    '    status = Column(String(50))\n',
    '\n'
]

# Insert before RemuneracaoCargo
inserted = False
for i, line in enumerate(lines):
    if 'class RemuneracaoCargo(Base):' in line:
        lines[i:i] = new_class
        inserted = True
        break

if inserted:
    with open('models.py', 'w') as f:
        f.writelines(lines)
    print("Successfully updated models.py")
else:
    print("Could not find RemuneracaoCargo in models.py")
    sys.exit(1)
