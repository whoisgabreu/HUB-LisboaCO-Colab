cat << 'EOF' > ollama-guia.md
# Guia de Instalação e Desinstalação do Ollama

## ✅ Instalação

### 1. Conectar na VPS
ssh usuario@ip_da_vps

### 2. Instalar o Ollama
curl -fsSL https://ollama.com/install.sh | sh

### 3. Verificar instalação
ollama --version

### 4. Testar modelo
ollama run llama3


---

## ❌ Desinstalação

### 1. Parar serviço
sudo systemctl stop ollama
sudo systemctl disable ollama

### 2. Remover binário
sudo rm /usr/local/bin/ollama

### 3. Remover serviço
sudo rm /etc/systemd/system/ollama.service
sudo systemctl daemon-reload

### 4. Remover modelos e dados
rm -rf ~/.ollama
sudo rm -rf /usr/share/ollama
sudo rm -rf /var/lib/ollama

### 5. Confirmar remoção
ollama --version

Se retornar "command not found", a remoção foi concluída com sucesso.
EOF