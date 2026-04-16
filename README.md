# TelemetryAI

Analista de telemetria com machine learning

---

## ⚠️ Aviso

Este projeto está em **fase alpha**.  
Pode conter bugs, instabilidades e mudanças frequentes.

---

## Como usar o app?

- Siga o passo a passo de instalação descrito abaixo, e após iniciar a janela irá aparecer uma tag com o status da telemetria(online/offline);
- Faça algumas voltas no jogo e já irão aparecer na aba histórico;
- Após concluir algumas sessões, vá até configurações->Treinamento do modelo ML e crie dados de treinamento do analista;
- Com os dados treinados, vá até histórico e selecione uma sessão que não foi usada para treinamento e clique em analisar volta;
- Na página de analise, selecione um dos treinamentos criados da mesma pista e selecione a volta que deseja analisar;

> Voltas com entrada nos boxes podem gerar analises não muito confiáveis

---

## 🖥️ Requisitos

- Windows 10 ou superior  
- Conexão com a internet  
- Permissão de administrador (caso o Python precise ser instalado)

---

## 🚀 Instalação Automática (Recomendado)

Este projeto inclui um instalador `.bat` que configura automaticamente o ambiente.

### 1. Baixe o projeto
``` bash
    git clone https://github.com/jungle34/TelemetryAI.git
    cd TelemetryAI
```

## 2. Execute o instalador

Dê dois cliques em:

```bash
    INSTALL_PROJECT_ALPHA.bat
```

ou execute via terminal:

```bash
    INSTALL_PROJECT_ALPHA.bat
```

## 3. O que o instalador faz

O script automaticamente:

Verifica se o Python está instalado
Instala o Python (caso necessário)
Atualiza o pip
Instala dependências do requirements.txt

### ▶️ Como executar

Após a instalação:
``` bash
    python main.py
```

# 🧪 Instalação Manual (opcional)
## 1. Instalar Python

Baixe em:
https://www.python.org/downloads/

## ⚠️ Marque a opção:

- 1. Add Python to PATH
- 2. Instalar dependências
```bash
    pip install -r requirements.txt
```
- 3. Rodar o projeto
``` bash
    python main.py
```

## 🔒 Licença

Este projeto está sob uma licença restrita de uso pessoal e confidencial.

Permissões:
Uso pessoal permitido
Modificações apenas locais
Restrições:
Proibida redistribuição
Proibido uso comercial
Proibido compartilhamento do código

Consulte o arquivo LICENSE para mais detalhes.