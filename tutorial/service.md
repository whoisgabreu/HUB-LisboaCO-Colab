# Como criar um Service para rodar Flask com Gunicorn automaticamente na VPS (systemd)

Este guia mostra como configurar um **service no systemd** para rodar uma aplicação **Flask** usando **Gunicorn**.
Com isso, sua aplicação:

* inicia automaticamente quando a VPS reinicia
* reinicia automaticamente caso o processo pare
* pode ser controlada com comandos do sistema

Tecnologias usadas:

* Flask
* Gunicorn
* systemd

---

# 1. Acessar a VPS

Conecte via SSH:

```bash
ssh usuario@ip_da_vps
```

---

# 2. Ir até o diretório do projeto

Exemplo:

```bash
cd /home/usuario/meu_projeto
```

---

# 3. Descobrir o caminho completo do projeto

Dentro da pasta do projeto execute:

```bash
pwd
```

Exemplo de retorno:

```
/home/usuario/meu_projeto
```

Guarde esse caminho.

---

# 4. Verificar o caminho do Gunicorn

Ative o ambiente virtual:

```bash
source venv/bin/activate
```

Agora execute:

```bash
which gunicorn
```

Exemplo de retorno:

```
/home/usuario/meu_projeto/venv/bin/gunicorn
```

Guarde esse caminho também.

---

# 5. Criar o arquivo de service

Crie o arquivo no systemd:

```bash
sudo nano /etc/systemd/system/flaskapp.service
```

---

# 6. Configurar o service

Exemplo de configuração:

```ini
[Unit]
Description=Gunicorn instance to serve Flask App
After=network.target

[Service]
User=usuario
Group=www-data
WorkingDirectory=/home/usuario/meu_projeto

Environment="PATH=/home/usuario/meu_projeto/venv/bin"

ExecStart=/home/usuario/meu_projeto/venv/bin/gunicorn -w 3 -b 0.0.0.0:5005 app:app

Restart=always

[Install]
WantedBy=multi-user.target
```

### Explicação dos campos

**WorkingDirectory**
Pasta onde está o projeto.

**Environment PATH**
Caminho do ambiente virtual.

**ExecStart**
Comando usado para iniciar o Gunicorn.

**app:app**

Formato:

```
arquivo_python:variavel_flask
```

Exemplo:

Arquivo:

```
app.py
```

Dentro dele:

```python
app = Flask(__name__)
```

---

# 7. Recarregar o systemd

Depois de salvar o arquivo:

```bash
sudo systemctl daemon-reload
```

---

# 8. Ativar inicialização automática

Isso faz o serviço iniciar junto com o servidor:

```bash
sudo systemctl enable flaskapp
```

---

# 9. Iniciar o serviço

```bash
sudo systemctl start flaskapp
```

---

# 10. Verificar o status

```bash
sudo systemctl status flaskapp
```

Se estiver funcionando aparecerá algo como:

```
Active: active (running)
```

---

# 11. Ver logs do serviço

Para ver logs em tempo real:

```bash
journalctl -u flaskapp -f
```

---

# 12. Comandos úteis

### Parar o serviço

```bash
sudo systemctl stop flaskapp
```

### Iniciar o serviço

```bash
sudo systemctl start flaskapp
```

### Reiniciar

```bash
sudo systemctl restart flaskapp
```

### Ver status

```bash
sudo systemctl status flaskapp
```

---

# 13. Se alterar o arquivo .service

Sempre execute:

```bash
sudo systemctl daemon-reload
sudo systemctl restart flaskapp
```

---

# 14. Teste de reinício automático

Reinicie a VPS:

```bash
sudo reboot
```

Depois que a VPS voltar, verifique:

```bash
sudo systemctl status flaskapp
```

Se estiver **active (running)**, o serviço está funcionando corretamente.

---

# Estrutura recomendada do projeto

```
meu_projeto/
│
├── app.py
├── requirements.txt
├── venv/
└── outras_pastas
```

---

# Dicas importantes

* Evite rodar aplicações dentro de `/root`
* Prefira usar `/home/usuario/projeto`
* Sempre use caminhos absolutos
* Use ambiente virtual (`venv`)

---

# Resultado final

Após essa configuração:

* sua API Flask roda com Gunicorn
* inicia automaticamente ao ligar a VPS
* reinicia automaticamente se falhar
* pode ser controlada pelo systemd
